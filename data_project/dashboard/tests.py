from django.test import SimpleTestCase
from django.urls import resolve
from dashboard import views
import numpy as np


class DashboardRoutesTests(SimpleTestCase):
    def test_dashboard_reports_route_resolves(self):
        match = resolve('/dashboard/reports/')
        self.assertEqual(match.func, views.reports)

    def test_dashboard_load_dataset_route_resolves(self):
        match = resolve('/dashboard/load-dataset/1/')
        self.assertEqual(match.func, views.load_dataset)

    def test_dashboard_activity_route_resolves(self):
        match = resolve('/dashboard/activity/')
        self.assertEqual(match.func, views.activity)

    def test_dashboard_delete_dataset_route_resolves(self):
        match = resolve('/dashboard/delete-dataset/1/')
        self.assertEqual(match.func, views.delete_dataset)

    def test_reports_page_renders_professional_report(self):
        response = self.client.get('/dashboard/reports/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Professional Report')
        self.assertEqual(response.context['active_section'], 'report')

    def test_normalize_report_data_converts_numpy_scalars(self):
        payload = views.normalize_report_data({
            'total_revenue': np.int64(100),
            'total_expense': np.int64(20),
            'net_profit': np.int64(80),
        })
        self.assertIsInstance(payload['total_revenue'], int)
        self.assertIsInstance(payload['net_profit'], int)
        self.assertEqual(payload['total_expense'], 20)
