from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .ai_service import AIServiceError, analyze_job_description, generate_interview_questions
from .forms import ApplicationForm, ApplicationSearchForm, InterviewForm
from .models import AIAnalysis, Application, Interview


def _user_applications(user):
    return Application.objects.filter(user=user)


@login_required
def dashboard(request):
    applications = _user_applications(request.user)

    status_counts = applications.values("status").annotate(total=Count("id"))
    status_map = {row["status"]: row["total"] for row in status_counts}
    status_summary = [
        {
            "key": key,
            "label": label,
            "count": status_map.get(key, 0),
        }
        for key, label in Application.Status.choices
    ]

    upcoming_interviews = (
        Interview.objects.filter(application__user=request.user, interview_date__gte=timezone.now())
        .select_related("application")
        .order_by("interview_date")[:5]
    )

    context = {
        "total_applications": applications.count(),
        "status_summary": status_summary,
        "recent_applications": applications.order_by("-created_at")[:5],
        "upcoming_interviews": upcoming_interviews,
    }
    return render(request, "tracker/dashboard.html", context)


@login_required
def application_list(request):
    applications = _user_applications(request.user)
    form = ApplicationSearchForm(request.GET or None)

    if form.is_valid():
        q = form.cleaned_data.get("q")
        status = form.cleaned_data.get("status")
        location = form.cleaned_data.get("location")
        category = form.cleaned_data.get("category")

        if q:
            applications = applications.filter(
                Q(job_title__icontains=q) | Q(company_name__icontains=q)
            )
        if status:
            applications = applications.filter(status=status)
        if location:
            applications = applications.filter(location__icontains=location)
        if category:
            applications = applications.filter(category__icontains=category)

    applications = applications.prefetch_related("tags").order_by("-updated_at")

    context = {
        "applications": applications,
        "form": form,
    }
    return render(request, "tracker/application_list.html", context)


@login_required
def application_detail(request, pk):
    application = get_object_or_404(Application, pk=pk, user=request.user)
    interviews = application.interviews.all()
    latest_analysis = application.ai_analyses.first()
    context = {
        "application": application,
        "interviews": interviews,
        "latest_analysis": latest_analysis,
    }
    return render(request, "tracker/application_detail.html", context)


@login_required
def application_create(request):
    if request.method == "POST":
        form = ApplicationForm(request.POST, user=request.user)
        if form.is_valid():
            application = form.save()
            messages.success(request, "Application created successfully.")
            return redirect("tracker:application_detail", pk=application.pk)
    else:
        form = ApplicationForm(user=request.user)

    return render(request, "tracker/application_form.html", {"form": form, "is_edit": False})


@login_required
def application_edit(request, pk):
    application = get_object_or_404(Application, pk=pk, user=request.user)
    if request.method == "POST":
        form = ApplicationForm(request.POST, instance=application, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Application updated successfully.")
            return redirect("tracker:application_detail", pk=application.pk)
    else:
        form = ApplicationForm(instance=application, user=request.user)

    return render(
        request,
        "tracker/application_form.html",
        {"form": form, "is_edit": True, "application": application},
    )


@login_required
def application_delete(request, pk):
    application = get_object_or_404(Application, pk=pk, user=request.user)
    if request.method == "POST":
        application.delete()
        messages.success(request, "Application deleted.")
        return redirect("tracker:application_list")
    return render(request, "tracker/application_confirm_delete.html", {"application": application})


@login_required
def interview_create(request, application_pk):
    application = get_object_or_404(Application, pk=application_pk, user=request.user)
    if request.method == "POST":
        form = InterviewForm(request.POST)
        if form.is_valid():
            interview = form.save(commit=False)
            interview.application = application
            interview.save()
            messages.success(request, "Interview added.")
            return redirect("tracker:application_detail", pk=application.pk)
    else:
        form = InterviewForm()
    return render(
        request,
        "tracker/interview_form.html",
        {"form": form, "application": application, "is_edit": False},
    )


@login_required
def interview_edit(request, application_pk, pk):
    application = get_object_or_404(Application, pk=application_pk, user=request.user)
    interview = get_object_or_404(Interview, pk=pk, application=application)
    if request.method == "POST":
        form = InterviewForm(request.POST, instance=interview)
        if form.is_valid():
            form.save()
            messages.success(request, "Interview updated.")
            return redirect("tracker:application_detail", pk=application.pk)
    else:
        form = InterviewForm(instance=interview)
    return render(
        request,
        "tracker/interview_form.html",
        {"form": form, "application": application, "is_edit": True, "interview": interview},
    )


@login_required
def interview_delete(request, application_pk, pk):
    application = get_object_or_404(Application, pk=application_pk, user=request.user)
    interview = get_object_or_404(Interview, pk=pk, application=application)
    if request.method == "POST":
        interview.delete()
        messages.success(request, "Interview removed.")
        return redirect("tracker:application_detail", pk=application.pk)
    return render(
        request,
        "tracker/interview_confirm_delete.html",
        {"application": application, "interview": interview},
    )


@login_required
def ai_analysis(request, application_pk):
    application = get_object_or_404(Application, pk=application_pk, user=request.user)

    if request.method == "POST":
        try:
            result = analyze_job_description(
                job_description=application.job_description,
                job_title=application.job_title,
                company_name=application.company_name,
            )
        except AIServiceError as exc:
            messages.error(request, str(exc))
            return redirect("tracker:application_detail", pk=application.pk)

        # Optional AI feature: also generate likely interview questions in the same run.
        questions = []
        try:
            questions = generate_interview_questions(
                job_description=application.job_description,
                job_title=application.job_title,
                company_name=application.company_name,
            )
        except AIServiceError:
            pass  # Non-fatal: the core analysis still succeeded.

        AIAnalysis.objects.create(
            application=application,
            summary=result["summary"],
            required_skills="\n".join(result["required_skills"]),
            required_experience=result["required_experience"],
            key_technologies="\n".join(result["key_technologies"]),
            interview_prep_suggestions="\n".join(result["interview_prep_suggestions"]),
            interview_questions="\n".join(questions),
        )
        messages.success(request, "AI analysis complete.")
        return redirect("tracker:application_detail", pk=application.pk)

    return render(request, "tracker/ai_analysis_confirm.html", {"application": application})
