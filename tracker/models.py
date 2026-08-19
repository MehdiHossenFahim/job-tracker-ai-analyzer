from django.conf import settings
from django.db import models
from django.urls import reverse


class Tag(models.Model):
    """A simple label users can attach to applications (e.g. 'Remote', 'Startup', 'Dream Job')."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tags")
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ["name"]
        unique_together = ("user", "name")

    def __str__(self):
        return self.name


class Application(models.Model):
    """A single job application tracked by a user."""

    class Status(models.TextChoices):
        WISHLIST = "wishlist", "Wishlist"
        APPLIED = "applied", "Applied"
        SCREENING = "screening", "Screening"
        INTERVIEW = "interview", "Interview"
        SELECTED = "selected", "Selected"
        REJECTED = "rejected", "Rejected"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="applications"
    )

    job_title = models.CharField(max_length=200)
    company_name = models.CharField(max_length=200)
    job_description = models.TextField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    salary = models.CharField(max_length=100, blank=True, help_text="e.g. $90,000 - $110,000")
    job_url = models.URLField(blank=True)

    application_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.WISHLIST)

    category = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g. Frontend, Backend, Data Science, Design",
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="applications")

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.job_title} @ {self.company_name}"

    def get_absolute_url(self):
        return reverse("tracker:application_detail", kwargs={"pk": self.pk})

    @property
    def status_badge_class(self):
        """Bootstrap-ish class suffix used for status pill coloring in templates."""
        return {
            self.Status.WISHLIST: "secondary",
            self.Status.APPLIED: "info",
            self.Status.SCREENING: "warning",
            self.Status.INTERVIEW: "primary",
            self.Status.SELECTED: "success",
            self.Status.REJECTED: "danger",
        }.get(self.status, "secondary")

    @property
    def upcoming_interview(self):
        from django.utils import timezone

        return self.interviews.filter(interview_date__gte=timezone.now()).order_by("interview_date").first()


class Interview(models.Model):
    """An interview round scheduled for a given application. One application can have many rounds."""

    class InterviewType(models.TextChoices):
        PHONE = "phone", "Phone Screen"
        VIDEO = "video", "Video Call"
        ONSITE = "onsite", "Onsite"
        TECHNICAL = "technical", "Technical"
        HR = "hr", "HR Round"
        OTHER = "other", "Other"

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="interviews")
    interview_date = models.DateTimeField()
    interview_type = models.CharField(
        max_length=20, choices=InterviewType.choices, default=InterviewType.VIDEO
    )
    meeting_link = models.URLField(blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["interview_date"]

    def __str__(self):
        return f"{self.get_interview_type_display()} - {self.application} ({self.interview_date:%Y-%m-%d %H:%M})"


class AIAnalysis(models.Model):
    """Stores the result of running the AI Job Description Analyzer on an application."""

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="ai_analyses")

    summary = models.TextField(blank=True)
    required_skills = models.TextField(blank=True, help_text="Newline-separated list")
    required_experience = models.TextField(blank=True)
    key_technologies = models.TextField(blank=True, help_text="Newline-separated list")
    interview_prep_suggestions = models.TextField(blank=True, help_text="Newline-separated list")
    match_notes = models.TextField(blank=True, help_text="Optional AI job-match commentary")
    interview_questions = models.TextField(
        blank=True, help_text="Newline-separated list of likely interview questions"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "AI Analysis"
        verbose_name_plural = "AI Analyses"

    def __str__(self):
        return f"AI Analysis for {self.application} ({self.created_at:%Y-%m-%d})"

    def skills_list(self):
        return [s.strip() for s in self.required_skills.splitlines() if s.strip()]

    def technologies_list(self):
        return [t.strip() for t in self.key_technologies.splitlines() if t.strip()]

    def prep_list(self):
        return [p.strip() for p in self.interview_prep_suggestions.splitlines() if p.strip()]

    def questions_list(self):
        return [q.strip() for q in self.interview_questions.splitlines() if q.strip()]
