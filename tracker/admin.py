from django.contrib import admin

from .models import AIAnalysis, Application, Interview, Tag


class InterviewInline(admin.TabularInline):
    model = Interview
    extra = 0


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("job_title", "company_name", "user", "status", "application_date", "updated_at")
    list_filter = ("status", "category")
    search_fields = ("job_title", "company_name", "location")
    inlines = [InterviewInline]


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ("application", "interview_type", "interview_date")
    list_filter = ("interview_type",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "user")


@admin.register(AIAnalysis)
class AIAnalysisAdmin(admin.ModelAdmin):
    list_display = ("application", "created_at")
