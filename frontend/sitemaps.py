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
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Get the current site's domain
        current_site = Site.objects.get_current()
        self.domain = current_site.domain

    def items(self):
        # Define URLs with their metadata
        url_configs = [
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
        
        # Ensure unique viewnames to prevent duplicates
        unique_urls = []
        seen = set()
        
        for url in url_configs:
            if url['viewname'] not in seen:
                seen.add(url['viewname'])
                unique_urls.append(url)
                
        logger.debug(f"Sitemap will include {len(unique_urls)} unique URLs")
        return unique_urls

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
            # Get all URLs from parent class
            urls = super().get_urls(*args, **kwargs)
            
            # Log the first few URLs for debugging
            logger.debug(f"Generated {len(urls)} URLs in sitemap")
            for i, url in enumerate(urls[:5]):  # Log first 5 URLs for debugging
                logger.debug(f"URL {i+1}: {getattr(url, 'location', str(url))}")
            
            return urls
            
        except Exception as e:
            logger.exception("Error generating sitemap URLs")
            raise
