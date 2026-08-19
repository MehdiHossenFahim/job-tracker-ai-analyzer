"""
Optional helper for generating demo data, useful when taking screenshots
or recording a demo video.

Usage:
    python manage.py seed_demo_data --username demo --password demopass123
"""

import datetime

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from tracker.models import Application, Interview, Tag


DEMO_JOBS = [
    {
        "job_title": "Backend Engineer",
        "company_name": "Nimbus Cloud",
        "job_description": (
            "We're looking for a Backend Engineer with 3+ years of experience in Python, "
            "Django, PostgreSQL, and REST API design. You'll build the services powering "
            "our data platform and collaborate closely with the frontend team."
        ),
        "location": "Remote",
        "salary": "$110,000 - $135,000",
        "status": Application.Status.APPLIED,
        "category": "Backend",
        "tags": ["Remote", "Dream Job"],
    },
    {
        "job_title": "Frontend Developer",
        "company_name": "Brightline Studio",
        "job_description": (
            "Seeking a Frontend Developer skilled in React, TypeScript, and Tailwind CSS. "
            "2+ years experience building responsive, accessible web apps required."
        ),
        "location": "New York, NY",
        "salary": "$95,000 - $115,000",
        "status": Application.Status.SCREENING,
        "category": "Frontend",
        "tags": ["Onsite"],
    },
    {
        "job_title": "Data Analyst",
        "company_name": "Harbor Insights",
        "job_description": (
            "Data Analyst role focused on SQL, Python, and dashboarding with Tableau. "
            "Entry level, 0-2 years experience welcome."
        ),
        "location": "Chicago, IL",
        "salary": "$70,000 - $85,000",
        "status": Application.Status.INTERVIEW,
        "category": "Data",
        "tags": ["Hybrid"],
    },
    {
        "job_title": "DevOps Engineer",
        "company_name": "Northgate Systems",
        "job_description": (
            "DevOps Engineer with experience in AWS, Docker, Kubernetes, and CI/CD pipelines. "
            "4+ years of experience preferred."
        ),
        "location": "Austin, TX",
        "salary": "$120,000 - $145,000",
        "status": Application.Status.WISHLIST,
        "category": "Infrastructure",
        "tags": ["Startup"],
    },
]


class Command(BaseCommand):
    help = "Seed demo applications, tags, and interviews for a user (for screenshots/demo)."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="demo")
        parser.add_argument("--password", default="demopass123")

    def handle(self, *args, **options):
        username = options["username"]
        password = options["password"]

        user, created = User.objects.get_or_create(username=username)
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created user '{username}'."))
        else:
            self.stdout.write(f"Using existing user '{username}'.")

        for i, job in enumerate(DEMO_JOBS):
            tags = job.pop("tags")
            application, _ = Application.objects.get_or_create(
                user=user,
                job_title=job["job_title"],
                company_name=job["company_name"],
                defaults={
                    **job,
                    "application_date": timezone.now().date() - datetime.timedelta(days=i * 3),
                },
            )
            tag_objs = []
            for name in tags:
                tag, _ = Tag.objects.get_or_create(user=user, name=name)
                tag_objs.append(tag)
            application.tags.set(tag_objs)

        interview_app = Application.objects.filter(
            user=user, status=Application.Status.INTERVIEW
        ).first()
        if interview_app and not interview_app.interviews.exists():
            Interview.objects.create(
                application=interview_app,
                interview_date=timezone.now() + datetime.timedelta(days=4),
                interview_type=Interview.InterviewType.VIDEO,
                meeting_link="https://meet.google.com/demo-link",
                notes="Focus on SQL and dashboarding case study.",
            )

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully."))
