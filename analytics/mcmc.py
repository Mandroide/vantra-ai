"""Inferencia bayesiana por MCMC (Metropolis-Hastings) sobre los resultados del held-out, en numpy puro.

Dos modelos:

1. Binomial con prior Beta(a, b), muestreado con Metropolis en escala logit. Tiene solución analítica conjugada
   (Beta(a + k, b + n - k)), que se usa para validar que el muestreador es correcto.

2. Modelo jerárquico logit para varios subgrupos (p. ej. registros lingüísticos):
       k_g ~ Binomial(n_g, p_g),   logit(p_g) = mu + tau * z_g
       mu ~ Normal(0, 1.5),   tau ~ HalfNormal(1),   z_g ~ Normal(0, 1)   (parametrización no centrada)
   Comparte información entre grupos pequeños (encogimiento parcial) y permite preguntas como
   P(p_coloquial < p_formal), que mide la brecha de equidad con su incertidumbre.

Diagnósticos: tasa de aceptación, R-hat dividido (Gelman-Rubin) y tamaño efectivo de muestra (ESS).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def _log_binom_lik(k, n, logit_p):
    # k*log(p) + (n-k)*log(1-p), estable numéricamente
    return k * -np.logaddexp(0, -logit_p) + (n - k) * -np.logaddexp(0, logit_p)


# ----------------------------------------------------------------------------- diagnósticos
def split_rhat(chains: np.ndarray) -> float:
    """chains: (m, n). R-hat dividido; valores cercanos a 1 (< 1.01) indican convergencia."""
    m, n = chains.shape
    half = n // 2
    x = np.concatenate([chains[:, :half], chains[:, half:2 * half]], axis=0)
    mm, nn = x.shape
    means = x.mean(axis=1)
    w = x.var(axis=1, ddof=1).mean()
    b = nn * means.var(ddof=1)
    var_hat = (nn - 1) / nn * w + b / nn
    return float(np.sqrt(var_hat / w)) if w > 0 else float("nan")


def ess(chains: np.ndarray) -> float:
    """Tamaño efectivo de muestra con autocorrelación promediada entre cadenas (secuencia inicial positiva)."""
    m, n = chains.shape
    x = chains - chains.mean(axis=1, keepdims=True)
    var = x.var(axis=1).mean()
    if var == 0:
        return float(m * n)
    acf = []
    for lag in range(1, min(n - 1, 1000)):
        rho = float(np.mean([np.dot(x[i, :-lag], x[i, lag:]) / (n * var) for i in range(m)]))
        if rho < 0.05:
            break
        acf.append(rho)
    tau = 1 + 2 * sum(acf)
    return float(m * n / tau)


@dataclass
class Fit:
    draws: dict[str, np.ndarray]  # parámetro -> (cadenas * muestras,)
    chains: dict[str, np.ndarray]  # parámetro -> (cadenas, muestras)
    acceptance: float
    rhat: dict[str, float] = field(default_factory=dict)
    ess: dict[str, float] = field(default_factory=dict)

    def summary(self, keys=None) -> dict:
        out = {}
        for k in keys or self.draws:
            d = self.draws[k]
            out[k] = {"media": float(d.mean()), "p05": float(np.quantile(d, 0.05)),
                      "p50": float(np.quantile(d, 0.50)), "p95": float(np.quantile(d, 0.95)),
                      "rhat": self.rhat.get(k), "ess": self.ess.get(k)}
        return out


# ----------------------------------------------------------------------------- modelo 1: Beta-Binomial
def beta_binomial(k: int, n: int, a: float = 1.0, b: float = 1.0, draws: int = 4000, burn: int = 1000,
                  chains: int = 4, step: float = 0.8, seed: int = 7) -> Fit:
    rng = np.random.default_rng(seed)

    def logpost(theta):  # theta = logit(p); incluye el jacobiano p(1-p)
        p_log = -np.logaddexp(0, -theta)
        q_log = -np.logaddexp(0, theta)
        return _log_binom_lik(k, n, theta) + a * p_log + b * q_log

    out = np.empty((chains, draws))
    accepted = 0
    for c in range(chains):
        theta = rng.normal(0, 1)
        lp = logpost(theta)
        for i in range(burn + draws):
            prop = theta + rng.normal(0, step)
            lp_prop = logpost(prop)
            if np.log(rng.random()) < lp_prop - lp:
                theta, lp = prop, lp_prop
                if i >= burn:
                    accepted += 1
            if i >= burn:
                out[c, i - burn] = theta
    p = sigmoid(out)
    return Fit(draws={"p": p.ravel()}, chains={"p": p}, acceptance=accepted / (chains * draws),
               rhat={"p": split_rhat(p)}, ess={"p": ess(p)})


# ----------------------------------------------------------------------------- modelo 2: jerárquico
def hierarchical(ks, ns, names, draws: int = 8000, burn: int = 3000, chains: int = 4, seed: int = 11) -> Fit:
    """Metropolis dentro de Gibbs con pasos adaptados durante el calentamiento."""
    ks, ns = np.asarray(ks, float), np.asarray(ns, float)
    g = len(ks)
    rng = np.random.default_rng(seed)

    def loglik(mu, log_tau, z):
        return float(np.sum(_log_binom_lik(ks, ns, mu + np.exp(log_tau) * z)))

    def logprior(mu, log_tau, z):
        tau = np.exp(log_tau)
        # Normal(0,1.5) para mu; HalfNormal(1) para tau con jacobiano de log_tau; Normal(0,1) para z
        return -0.5 * (mu / 1.5) ** 2 - 0.5 * tau ** 2 + log_tau - 0.5 * float(np.sum(z ** 2))

    store = {n: np.empty((chains, draws)) for n in names}
    store_mu, store_tau = np.empty((chains, draws)), np.empty((chains, draws))
    acc_total, prop_total = 0, 0
    for c in range(chains):
        mu, log_tau, z = rng.normal(0, 0.5), np.log(0.5), rng.normal(0, 0.5, g)
        steps = np.full(g + 2, 0.5)
        accs = np.zeros(g + 2)
        lp = loglik(mu, log_tau, z) + logprior(mu, log_tau, z)
        for i in range(burn + draws):
            for j in range(g + 2):  # actualiza un parámetro a la vez
                mu2, lt2, z2 = mu, log_tau, z.copy()
                if j == 0:
                    mu2 = mu + rng.normal(0, steps[0])
                elif j == 1:
                    lt2 = log_tau + rng.normal(0, steps[1])
                else:
                    z2[j - 2] += rng.normal(0, steps[j])
                lp2 = loglik(mu2, lt2, z2) + logprior(mu2, lt2, z2)
                ok = np.log(rng.random()) < lp2 - lp
                if ok:
                    mu, log_tau, z, lp = mu2, lt2, z2, lp2
                accs[j] += ok
                if i >= burn:
                    acc_total += ok
                    prop_total += 1
            if i < burn and (i + 1) % 100 == 0:  # adapta el paso hacia ~35-45% de aceptación
                rate = accs / 100
                steps *= np.where(rate > 0.45, 1.25, np.where(rate < 0.30, 0.8, 1.0))
                accs[:] = 0
            if i >= burn:
                p = sigmoid(mu + np.exp(log_tau) * z)
                for gi, n in enumerate(names):
                    store[n][c, i - burn] = p[gi]
                store_mu[c, i - burn], store_tau[c, i - burn] = mu, np.exp(log_tau)
    chains_d = {**store, "mu": store_mu, "tau": store_tau}
    return Fit(draws={k: v.ravel() for k, v in chains_d.items()}, chains=chains_d,
               acceptance=acc_total / max(prop_total, 1),
               rhat={k: split_rhat(v) for k, v in chains_d.items()},
               ess={k: ess(v) for k, v in chains_d.items()})
