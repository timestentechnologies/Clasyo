from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from datetime import datetime

class StaticViewSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8
    protocol = 'https'

    def items(self):
        return [
            'frontend:home',
            'frontend:about',
            'frontend:pricing',
            'frontend:contact',
            'frontend:faq',
            'frontend:privacy',
            'frontend:terms',
            'frontend:license',
            'frontend:documentation',
        ]

    def location(self, item):
        return reverse(item)

    def lastmod(self, item):
        # Return the last modified date of each page
        # For now, return current date since we don't track modifications
        return datetime.now()
