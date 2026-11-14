"""Source registry. To support a new ATS: add a module with fetch(entry) -> list[Job]
and register it here. To add a company: edit config/sources.yaml only."""
from . import aggregator, apple, ashby, comeet, greenhouse, lever, workday

FETCHERS = {
    "greenhouse": greenhouse.fetch,
    "lever": lever.fetch,
    "ashby": ashby.fetch,
    "comeet": comeet.fetch,
    "apple": apple.fetch,
    "workday": workday.fetch,
    "aggregator": aggregator.fetch,
}
