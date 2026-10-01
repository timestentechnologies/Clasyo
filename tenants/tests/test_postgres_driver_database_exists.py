from unittest.mock import MagicMock, patch

import psycopg2
from django.test import SimpleTestCase, override_settings

POSTGRES_DEFAULT = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'postgres',
        'USER': 'app_user',
        'PASSWORD': 'secret',
        'HOST': 'db.example.com',
        'PORT': 5432,
    }
}


@override_settings(DATABASES=POSTGRES_DEFAULT)
class PostgresTenantDriverDatabaseExistsTests(SimpleTestCase):
    @patch('psycopg2.connect')
    def test_missing_database_returns_false(self, mock_connect):
        from tenants.drivers import PostgresTenantDriver

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        self.assertFalse(PostgresTenantDriver().database_exists('missing-tenant'))

    @patch('psycopg2.connect')
    def test_existing_database_returns_true(self, mock_connect):
        from tenants.drivers import PostgresTenantDriver

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        self.assertTrue(PostgresTenantDriver().database_exists('timesten-academy'))

    @patch('psycopg2.connect')
    def test_connection_error_propagates(self, mock_connect):
        from tenants.drivers import PostgresTenantDriver

        mock_connect.side_effect = psycopg2.OperationalError('connection refused')

        with self.assertRaises(psycopg2.OperationalError):
            PostgresTenantDriver().database_exists('any-tenant')

    @patch('psycopg2.connect')
    def test_authentication_error_propagates(self, mock_connect):
        from tenants.drivers import PostgresTenantDriver

        mock_connect.side_effect = psycopg2.OperationalError('password authentication failed')

        with self.assertRaises(psycopg2.OperationalError):
            PostgresTenantDriver().database_exists('any-tenant')
