from django.views.generic import TemplateView


class LandingPageView(TemplateView):
	template_name = 'landingPage.html'


class HomeView(TemplateView):
	template_name = 'home.html'

