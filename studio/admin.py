from django.contrib import admin

from .models import (ClientProject, ClientRequest, DesignProposal, Milestone, ProjectDocument, ProposalComment,
                     ProposalImage, SiteUpdate, Task)


class MilestoneInline(admin.TabularInline):
    model = Milestone
    extra = 0


@admin.register(ClientProject)
class ClientProjectAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "client_name", "stage", "designer", "start_date", "budget"]
    list_filter = ["stage"]
    search_fields = ["code", "name", "client_name"]
    inlines = [MilestoneInline]


class ProposalImageInline(admin.TabularInline):
    model = ProposalImage
    extra = 0


@admin.register(DesignProposal)
class DesignProposalAdmin(admin.ModelAdmin):
    list_display = ["project", "version", "title", "status"]
    inlines = [ProposalImageInline]


admin.site.register([Task, ProposalComment, SiteUpdate, ProjectDocument, ClientRequest])
