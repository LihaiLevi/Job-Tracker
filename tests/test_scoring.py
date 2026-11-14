import unittest
from pathlib import Path

import yaml

from src.models import Job
from src.scoring import Scorer, required_years

PROFILE = yaml.safe_load((Path(__file__).resolve().parent.parent / "config" / "profile.yaml")
                         .read_text(encoding="utf-8"))
SCORER = Scorer(PROFILE)

GOOD_DESC = ("We build mission-critical avionics for UAV ground control. Requirements: "
             "4+ years of experience in C/C++, RTOS (VxWorks), embedded Linux, TCP/IP, UDP.")


def job(title="Embedded Software Engineer", location="Tel Aviv, Israel", desc=GOOD_DESC, **kw):
    return Job(id=kw.pop("id", "t:1"), source="test", company=kw.pop("company", "Acme"),
               title=title, location=location, url="https://x", description=desc, **kw)


class TestRequiredYears(unittest.TestCase):
    def test_patterns(self):
        self.assertEqual(required_years("5+ years of experience in C++"), 5)
        self.assertEqual(required_years("3-5 years experience"), 3)
        self.assertEqual(required_years("at least 4 years in embedded"), 4)
        self.assertEqual(required_years("Minimum of 8 years"), 8)
        self.assertEqual(required_years("3+ years C, 6+ years of experience overall"), 6)
        self.assertEqual(required_years("לפחות 5 שנות ניסיון בפיתוח"), 5)

    def test_ignores_boilerplate(self):
        self.assertIsNone(required_years("For 30 years we have innovated."))
        self.assertIsNone(required_years("Founded 10 years ago in Tel Aviv"))
        self.assertIsNone(required_years(""))


class TestScoring(unittest.TestCase):
    def test_ideal_job_matches(self):
        r = SCORER.score(job())
        self.assertEqual(r.status, "match", r.reasons)
        self.assertGreaterEqual(r.score, 70)

    def test_hebrew_title_matches(self):
        r = SCORER.score(job(title="מהנדס/ת תוכנה משובצת זמן אמת", location="הרצליה"))
        self.assertEqual(r.status, "match", r.reasons)

    def test_rejected_seniority_words(self):
        for t in ["Embedded Software Intern", "Junior Firmware Engineer", "Student - Embedded",
                  "Principal Embedded Engineer", "Staff Firmware Engineer",
                  "Embedded Software Manager", "Director of Firmware", "VP R&D",
                  "Head of Embedded"]:
            self.assertEqual(SCORER.score(job(title=t)).status, "reject", t)

    def test_rejects_8_plus_years(self):
        r = SCORER.score(job(desc="8+ years of experience in embedded C++ RTOS"))
        self.assertEqual(r.status, "reject")

    def test_senior_rules(self):
        ok = SCORER.score(job(title="Senior Embedded Software Engineer",
                              desc="5+ years of experience with C++, RTOS, VxWorks"))
        self.assertEqual(ok.status, "match", ok.reasons)
        too_many = SCORER.score(job(title="Senior Embedded Software Engineer",
                                    desc="7+ years of experience with C++ and RTOS"))
        self.assertEqual(too_many.status, "reject")
        unknown = SCORER.score(job(title="Senior Embedded Software Engineer"))
        plain = SCORER.score(job())
        self.assertNotEqual(unknown.status, "reject")
        self.assertLess(unknown.score, plain.score + 1)   # senior w/o years: penalty applied

    def test_non_senior_with_7_years_still_ok(self):
        r = SCORER.score(job(desc="7 years of experience in C++ RTOS embedded linux"))
        self.assertNotEqual(r.status, "reject")

    def test_comeet_entry_level_rejected(self):
        r = SCORER.score(job(desc="Experience level: Entry-level\n" + GOOD_DESC))
        self.assertEqual(r.status, "reject")

    def test_irrelevant_titles_rejected(self):
        for t in ["Frontend Developer", "Full Stack Engineer", "Data Scientist",
                  "Sales Engineer", "Product Manager", "DevOps Engineer", "ASIC Design Engineer"]:
            self.assertEqual(SCORER.score(job(title=t)).status, "reject", t)

    def test_location(self):
        self.assertEqual(SCORER.score(job(location="New York, NY")).status, "reject")
        self.assertEqual(SCORER.score(job(location="Remote - US")).status, "reject")
        self.assertEqual(SCORER.score(job(location="")).status, "reject")
        tlv = SCORER.score(job(location="Tel Aviv")).score
        center = SCORER.score(job(location="Rehovot, Israel")).score
        haifa = SCORER.score(job(location="Haifa, Israel")).score
        self.assertGreater(tlv, center)
        self.assertGreater(center, haifa)
        self.assertEqual(SCORER.score(job(location="Remote, Israel")).status, "match")
        self.assertEqual(SCORER.score(job(location="Remote (EMEA)")).status, "match")
        self.assertEqual(SCORER.score(job(location="Munich / Tel Aviv")).status, "match")
        # Telegram notify region filter: only 'north' is enabled in notify_tiers
        self.assertTrue(SCORER.in_notify_region(job(location="Haifa, Israel")))
        self.assertTrue(SCORER.in_notify_region(job(location="Israel, Tel Aviv / Israel, Yokneam")))
        self.assertFalse(SCORER.in_notify_region(job(location="Tel Aviv, Israel")))
        self.assertFalse(SCORER.in_notify_region(job(location="Jerusalem, Israel")))

    def test_generic_title_is_at_most_borderline(self):
        r = SCORER.score(job(title="Software Engineer"))
        self.assertIn(r.status, ("borderline", "reject"))

    def test_weak_embedded_title_without_skills(self):
        r = SCORER.score(job(title="Embedded Engineer", desc="Great team, free lunch.",
                             location="Haifa"))
        self.assertNotEqual(r.status, "match")

    def test_expanded_role_types_and_mid_level_override(self):
        # "Junior / Mid-level" should not be rejected on 'junior'
        r_mid = SCORER.score(job(title="Junior / Mid-level Software Engineer (Rust / C++ / GPU)",
                                 location="Haifa, Israel",
                                 desc="1-3 years experience in C++, real-time, drone systems."))
        self.assertEqual(r_mid.status, "match", r_mid.reasons)

        # "(C)" in title + C++11/14 in description
        r_c = SCORER.score(job(title="Senior Software Engineer (C)",
                               location="Tel Aviv, Israel",
                               desc="At least 5 years of experience in C++11/14, real-time, TCP/IP, Linux kernel."))
        self.assertEqual(r_c.status, "match", r_c.reasons)

        # Linux / OS / Robotics / Data Path role titles
        for t in [
            "Experienced Software Linux Integration Engineer - OS team",
            "Robotics Software Engineer",
            "Software Engineer - Data Path",
            "Lead Flight Control Engineer - Tactical Munitions",
            "Senior Software Engineer – Autonomous Command & Control Platform",
        ]:
            res = SCORER.score(job(title=t, location="Tel Aviv, Israel", desc=GOOD_DESC))
            self.assertEqual(res.status, "match", f"{t}: {res.reasons}")


if __name__ == "__main__":
    unittest.main()
