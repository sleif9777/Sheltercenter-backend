from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RangeDateTimeFilter

from .models import ChatbotInteraction, PolicyEntry


@admin.register(PolicyEntry)
class PolicyEntryAdmin(ModelAdmin):
    list_display = ("slug", "title", "is_active", "updated_instant")
    list_display_links = ("slug", "title")
    list_filter = ("is_active",)
    search_fields = ("slug", "title", "body")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(ChatbotInteraction)
class ChatbotInteractionAdmin(ModelAdmin):
    list_display = (
        "id",
        "created_instant",
        "adopter",
        "question",
        "bot_reason",
        "category",
        "bot_escalated",
        "adopter_escalated",
        "backlog_status",
        "review",
    )
    list_display_links = ("id", "question")
    list_select_related = ("adopter__user_profile",)
    list_filter = (
        ("backlog_status", ChoicesDropdownFilter),
        ("review", ChoicesDropdownFilter),
        "bot_escalated",
        "adopter_escalated",
        "category",
        "knowledge_base_version",
        ("created_instant", RangeDateTimeFilter),
    )
    list_filter_submit = True
    search_fields = ("question", "answer", "adopter__primary_email")
    autocomplete_fields = ("adopter", "resolved_by_policy")
    readonly_fields = (
        "created_instant",
        "adopter",
        "question",
        "message_html",
        "answer",
        "bot_reason",
        "category",
        "cited_policies",
        "offered_appointment",
        "offer_accepted_instant",
        "bot_escalated",
        "adopter_escalated",
        "model",
        "knowledge_base_version",
        "input_tokens",
        "cache_read_tokens",
        "output_tokens",
    )
    exclude = ("reviewed_by",)
    date_hierarchy = "created_instant"

    def save_model(self, request, obj, form, change) -> None:  # type: ignore[no-untyped-def]
        if "review" in form.changed_data or "review_notes" in form.changed_data:
            obj.reviewed_by = request.user
        super().save_model(request, obj, form, change)
