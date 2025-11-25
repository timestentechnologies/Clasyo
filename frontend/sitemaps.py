import logging
from django.contrib.sitemaps import Sitemap
from django.contrib.sites.models import Site
from django.urls import reverse, NoReverseMatch
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)

class StaticViewSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8
    protocol = 'https'
    i18n = True
    limit = 1000  # Max number of URLs per sitemap page
    template_name = 'sitemap.xml'  # Explicitly set the template name
    
    def __init__(self):
        # Get the current site's domain
        current_site = Site.objects.get_current()
        self.domain = current_site.domain

    def items(self):
        urls = [
            {'viewname': 'frontend:home', 'priority': 1.0, 'changefreq': 'daily'},
            {'viewname': 'frontend:about', 'priority': 0.8, 'changefreq': 'weekly'},
            {'viewname': 'frontend:pricing', 'priority': 0.7, 'changefreq': 'weekly'},
            {'viewname': 'frontend:contact', 'priority': 0.5, 'changefreq': 'monthly'},
            {'viewname': 'frontend:faq', 'priority': 0.6, 'changefreq': 'weekly'},
            {'viewname': 'frontend:privacy', 'priority': 0.3, 'changefreq': 'monthly'},
            {'viewname': 'frontend:terms', 'priority': 0.3, 'changefreq': 'monthly'},
            {'viewname': 'frontend:license', 'priority': 0.3, 'changefreq': 'monthly'},
            {'viewname': 'frontend:documentation', 'priority': 0.7, 'changefreq': 'weekly'},
        ]
        logger.debug(f"Sitemap will include {len(urls)} URLs")
        return urls

    def location(self, item):
        try:
            url = reverse(item['viewname'])
            logger.debug(f"Generated URL for {item['viewname']}: {url}")
            return url
        except NoReverseMatch as e:
            logger.error(f"Failed to reverse URL for {item['viewname']}: {str(e)}")
            return ''
            
    def priority(self, item):
        return item.get('priority', 0.5)
        
    def changefreq(self, item):
        return item.get('changefreq', 'weekly')
        
    def lastmod(self, item):
        # Return the current time for all pages
        return timezone.now()
        
    def get_urls(self, *args, **kwargs):
        logger.debug("Generating sitemap URLs...")
        try:
            urls = super().get_urls(*args, **kwargs)
            logger.debug(f"Successfully generated {len(urls)} sitemap URLs")
            return urls
        except Exception as e:
            logger.exception("Error generating sitemap URLs")
            raise
