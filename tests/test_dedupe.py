import unittest

from src.models import Job, ScoreResult
from src.store import Store

MATCH = ScoreResult(80, "match", ["test"])


def job(id="greenhouse:acme:1", title="Embedded Software Engineer", location="Tel Aviv", company="Acme"):
    return Job(id=id, source="greenhouse", company=company, title=title, location=location,
               url="https://x")


class TestDedupe(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:")

    def test_new_job_not_notified(self):
        j = job()
        self.store.upsert(j, MATCH)
        self.assertFalse(self.store.already_notified(j))

    def test_same_id_never_twice(self):
        j = job()
        self.store.upsert(j, MATCH)
        self.store.mark_notified([j.id])
        self.store.upsert(j, MATCH)          # seen again next run
        self.assertTrue(self.store.already_notified(j))

    def test_repost_with_new_id_is_deduped(self):
        old = job(id="greenhouse:acme:1")
        self.store.upsert(old, MATCH)
        self.store.mark_notified([old.id])
        repost = job(id="greenhouse:acme:999", title="  Embedded  Software Engineer ")
        self.store.upsert(repost, MATCH)
        self.assertTrue(self.store.already_notified(repost))

    def test_different_job_not_deduped(self):
        a = job(id="a:1")
        self.store.upsert(a, MATCH)
        self.store.mark_notified([a.id])
        b = job(id="a:2", title="Firmware Engineer")
        self.assertFalse(self.store.already_notified(b))
        c = job(id="a:3", location="Haifa")
        self.assertFalse(self.store.already_notified(c))

    def test_upsert_keeps_first_seen_and_llm_verdict(self):
        j = job()
        self.store.upsert(j, ScoreResult(40, "borderline", []), "yes: good fit")
        first = self.store.get(j.id)["first_seen"]
        j2 = job()
        j2.first_seen = "2099-01-01T00:00:00+00:00"
        self.store.upsert(j2, ScoreResult(40, "borderline", []), None)
        row = self.store.get(j.id)
        self.assertEqual(row["first_seen"], first)
        self.assertEqual(row["llm_verdict"], "yes: good fit")

    def test_fingerprint_normalization(self):
        self.assertEqual(job(title="Embedded SW Engineer!").fingerprint,
                         job(title="embedded sw engineer").fingerprint)


if __name__ == "__main__":
    unittest.main()
