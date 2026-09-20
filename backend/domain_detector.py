"""Detect dataset domain to drive domain-specific analysis."""
import re
from typing import Literal

Domain = Literal[
    "climate", "healthcare", "transportation", "financial",
    "genomics", "energy", "events", "materials", "scientific", "general"
]

_DOMAIN_KEYWORDS: dict[Domain, list[str]] = {
    "climate": ["temperature", "temp", "pressure", "humidity", "wind", "rainfall",
                 "precipitation", "weather", "climate", "snow", "storm", "flood",
                 "drought", "extreme", "forecast", "noaa", "isd", "station", "dewpoint",
                 "visibility", "cloud", "radiation", "solar"],
    "healthcare": ["patient", "diagnosis", "treatment", "hospital", "mortality",
                   "survival", "disease", "symptom", "medication", "dosage", "clinical",
                   "health", "medical", "bmi", "blood", "heart", "cancer", "diabetes"],
    "transportation": ["taxi", "trip", "fare", "pickup", "dropoff", "route", "speed",
                       "traffic", "vehicle", "driver", "distance", "duration", "ride",
                       "uber", "lyft", "tlc", "passenger", "origin", "destination"],
    "financial": ["price", "return", "volume", "stock", "market", "revenue", "profit",
                  "loss", "gdp", "inflation", "rate", "yield", "bond", "equity", "cost",
                  "income", "expense", "trade", "currency", "dollar"],
    "genomics": ["gene", "sequence", "snp", "allele", "chromosome", "protein",
                 "mutation", "expression", "genome", "dna", "rna", "variant",
                 "phenotype", "trait", "locus", "nucleotide"],
    "energy": ["energy", "power", "electricity", "grid", "utility", "capacity",
               "consumption", "generation", "renewable", "solar", "wind", "fuel",
               "emission", "carbon", "mwh", "kwh", "eia", "ferc", "pudl"],
    "events": ["event", "tone", "sentiment", "news", "media", "actor", "country",
               "gdelt", "conflict", "protest", "article", "source", "mention"],
    "materials": ["material", "structure", "property", "bandgap", "formation",
                  "energy", "crystal", "element", "compound", "magnetic", "elastic",
                  "density", "conductivity", "stability"],
}


def detect_domain(schema: dict, intent: str = "") -> Domain:
    text = " ".join([
        intent.lower(),
        " ".join(schema.get("columns", {}).keys()).lower()
    ])
    scores: dict[Domain, int] = {d: 0 for d in _DOMAIN_KEYWORDS}
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if re.search(r'\b' + re.escape(kw) + r'\b', text):
                scores[domain] += 1
    best = max(scores, key=lambda d: scores[d])
    return best if scores[best] >= 1 else "general"


def get_domain_system_prompt(domain: Domain) -> str:
    prompts = {
        "climate": "You are a senior climate scientist and data analyst specialising in atmospheric data, extreme weather events, and environmental time series. Use meteorological terminology where appropriate.",
        "healthcare": "You are a senior biostatistician and clinical data analyst specialising in epidemiology and patient outcomes. Use appropriate statistical rigor and clinical framing.",
        "transportation": "You are a senior urban mobility analyst specialising in transportation networks, demand patterns, and ride-hailing economics.",
        "financial": "You are a senior quantitative analyst specialising in financial time series, risk, and market microstructure.",
        "genomics": "You are a senior computational biologist specialising in genomic data analysis, variant interpretation, and population genetics.",
        "energy": "You are a senior energy systems analyst specialising in electricity markets, grid reliability, and renewable integration.",
        "events": "You are a senior data journalist and geopolitical analyst specialising in media event data and sentiment trends.",
        "materials": "You are a senior materials scientist and computational chemistry analyst specialising in structure-property relationships.",
        "scientific": "You are a senior data scientist specialising in experimental data analysis and scientific discovery.",
        "general": "You are a senior quantitative data analyst with broad expertise across statistics, machine learning, and data science.",
    }
    return prompts.get(domain, prompts["general"])
