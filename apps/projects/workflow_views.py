from django.shortcuts import render
from django.views.generic import TemplateView

class WorkflowDiagramsView(TemplateView):
    """View to display workflow diagrams"""
    template_name = 'workflow_diagrams.html'