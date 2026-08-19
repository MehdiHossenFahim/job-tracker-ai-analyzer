from django import forms

from .models import Application, Interview, Tag


class ApplicationForm(forms.ModelForm):
    tags_input = forms.CharField(
        required=False,
        label="Tags",
        help_text="Comma-separated, e.g. Remote, Dream Job, Startup",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Remote, Dream Job"}),
    )

    class Meta:
        model = Application
        fields = [
            "job_title",
            "company_name",
            "job_description",
            "location",
            "salary",
            "job_url",
            "application_date",
            "status",
            "category",
            "notes",
        ]
        widgets = {
            "job_title": forms.TextInput(attrs={"class": "form-control"}),
            "company_name": forms.TextInput(attrs={"class": "form-control"}),
            "job_description": forms.Textarea(attrs={"class": "form-control", "rows": 6}),
            "location": forms.TextInput(attrs={"class": "form-control"}),
            "salary": forms.TextInput(attrs={"class": "form-control"}),
            "job_url": forms.URLInput(attrs={"class": "form-control"}),
            "application_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "category": forms.TextInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["tags_input"].initial = ", ".join(
                self.instance.tags.values_list("name", flat=True)
            )

    def save(self, commit=True):
        application = super().save(commit=False)
        if self.user is not None:
            application.user = self.user
        if commit:
            application.save()
            self._save_tags(application)
        return application

    def _save_tags(self, application):
        raw = self.cleaned_data.get("tags_input", "")
        names = [n.strip() for n in raw.split(",") if n.strip()]
        tag_objs = []
        for name in names:
            tag, _ = Tag.objects.get_or_create(user=self.user, name=name)
            tag_objs.append(tag)
        application.tags.set(tag_objs)

    def save_m2m_tags(self, application):
        # Helper for callers using commit=False then calling save() separately.
        self._save_tags(application)


class InterviewForm(forms.ModelForm):
    class Meta:
        model = Interview
        fields = ["interview_date", "interview_type", "meeting_link", "notes"]
        widgets = {
            "interview_date": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "interview_type": forms.Select(attrs={"class": "form-select"}),
            "meeting_link": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://..."}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class ApplicationSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Search",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Search job title or company..."}
        ),
    )
    status = forms.ChoiceField(
        required=False,
        choices=[("", "All Statuses")] + list(Application.Status.choices),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    location = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Location"}),
    )
    category = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Category"}),
    )
