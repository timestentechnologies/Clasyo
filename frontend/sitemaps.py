from django.contrib.sitemaps import Sitemap
from django.urls import reverse, NoReverseMatch
from django.utils import timezone
from datetime import datetime

class StaticViewSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8
    protocol = 'https'
    i18n = True

    def items(self):
        return [
            {'viewname': 'frontend:home', 'priority': 1.0},
            {'viewname': 'frontend:about', 'priority': 0.8},
            {'viewname': 'frontend:pricing', 'priority': 0.7},
            {'viewname': 'frontend:contact', 'priority': 0.5},
            {'viewname': 'frontend:faq', 'priority': 0.6},
            {'viewname': 'frontend:privacy', 'priority': 0.3},
            {'viewname': 'frontend:terms', 'priority': 0.3},
            {'viewname': 'frontend:license', 'priority': 0.3},
            {'viewname': 'frontend:documentation', 'priority': 0.7},
        ]

    def location(self, item):
        try:
            return reverse(item['viewname'])
        except NoReverseMatch:
            return ''
            
    def priority(self, item):
        return item.get('priority', 0.5)
        
    def lastmod(self, item):
        # Return the current time for all pages
        return timezone.now()

    def lastmod(self, item):
        # Return the last modified date of each page
        # For now, return current date since we don't track modifications
        return datetime.now()
