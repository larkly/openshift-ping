"""Unit tests for openshift-ping app.

Uses Flask test client + unittest.mock for subprocess patching.
Run with: python -m unittest discover -s . -p "test_*.py" -v
"""

import os
import sys
import subprocess
import unittest
from unittest import mock

# Ensure app is importable
sys.path.insert(0, os.path.dirname(__file__))

import app as app_module
from app import _filter_stderr, filter_output


class FilterStderrTests(unittest.TestCase):
    """Tests for _filter_stderr (issue #6 fix)."""

    def test_filters_libnss_warning(self):
        """The libnss_wrapper.so warning should be removed."""
        stderr = (
            "ERROR: ld.so: object 'libnss_wrapper.so' from "
            "LD_PRELOAD cannot be preloaded: ignored."
        )
        result = _filter_stderr(stderr)
        self.assertEqual(result, '')

    def test_filters_ld_preload_line(self):
        """Lines mentioning LD_PRELOAD should be removed."""
        stderr = "ld.so: object 'libnss_wrapper.so' from LD_PRELOAD cannot be preloaded"
        result = _filter_stderr(stderr)
        self.assertEqual(result, '')

    def test_keeps_real_stderr(self):
        """Real error messages should be kept."""
        stderr = "ping: unknown host badhost"
        result = _filter_stderr(stderr)
        self.assertEqual(result, 'ping: unknown host badhost')

    def test_empty_stderr(self):
        """Empty stderr should return empty."""
        self.assertEqual(_filter_stderr(''), '')
        self.assertIsNone(_filter_stderr(None))

    def test_mixed_stderr(self):
        """Only noise lines should be removed, real errors kept."""
        stderr = (
            "ERROR: ld.so: object 'libnss_wrapper.so' from LD_PRELOAD cannot be preloaded: ignored.\n"
            "ping: unknown host foo"
        )
        result = _filter_stderr(stderr)
        self.assertEqual(result, 'ping: unknown host foo')


class FilterOutputTests(unittest.TestCase):
    """Tests for filter_output (issue #6 fix at integration level)."""

    def _make_mock_proc(self, stdout='', stderr=''):
        proc = mock.MagicMock()
        proc.communicate.return_value = (stdout, stderr)
        return proc, stdout, stderr

    def test_no_stderr_returns_just_host_and_stdout(self):
        proc, stdout, _ = self._make_mock_proc(stdout='4 packets received')
        result = filter_output(proc=proc, host='10.0.0.1', time_limit=10)
        self.assertIn('10.0.0.1', result)
        self.assertIn('4 packets received', result)
        self.assertNotIn('stderr', result)

    def test_only_noise_stderr_filtered_out(self):
        """If stderr is only noise, it should not appear in output."""
        proc, stdout, _ = self._make_mock_proc(
            stdout='4 packets received',
            stderr="ld.so: object 'libnss_wrapper.so' from LD_PRELOAD cannot be preloaded: ignored."
        )
        result = filter_output(proc=proc, host='10.0.0.1', time_limit=10)
        self.assertNotIn('stderr', result)
        self.assertNotIn('libnss_wrapper', result)

    def test_real_stderr_included(self):
        """Real error in stderr should appear in output."""
        proc, stdout, _ = self._make_mock_proc(
            stdout='',
            stderr='ping: unknown host nonexistent.invalid'
        )
        result = filter_output(proc=proc, host='nonexistent.invalid', time_limit=10)
        self.assertIn('stderr', result)
        self.assertIn('unknown host', result)

    def test_timeout_handled(self):
        """TimeoutExpired should be handled gracefully."""
        proc = mock.MagicMock()
        proc.communicate.side_effect = [
            subprocess.TimeoutExpired(cmd='ping', timeout=10),
            ('partial output after kill', ''),
        ]
        result = filter_output(proc=proc, host='10.0.0.1', time_limit=10)
        self.assertIn('10.0.0.1', result)
        self.assertIn('partial output after kill', result)
        # proc.kill should have been called
        proc.kill.assert_called_once()


class IndexRouteTests(unittest.TestCase):
    """Tests for the root route."""

    def setUp(self):
        self.app = app_module.app
        self.client = self.app.test_client()

    def test_index_redirects_to_ping(self):
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/ping', resp.headers.get('Location', ''))


class PingRouteTests(unittest.TestCase):
    """Tests for the /ping route (issue #5 fix)."""

    def setUp(self):
        self.app = app_module.app
        self.client = self.app.test_client()
        # Clear any env var that might interfere
        self._orig_env = os.environ.pop('PING_TARGET', None)
        self._orig_target = os.environ.pop('target', None)

    def tearDown(self):
        if self._orig_env is not None:
            os.environ['PING_TARGET'] = self._orig_env
        if self._orig_target is not None:
            os.environ['target'] = self._orig_target

    def test_no_host_no_env_shows_instruction(self):
        """Without host or env var, show the instruction message."""
        resp = self.client.get('/ping/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'IP address', resp.data)

    def test_no_host_uses_env_var(self):
        """Without host but with PING_TARGET set, ping that host (issue #5)."""
        os.environ['PING_TARGET'] = '10.0.0.1'
        mock_proc = mock.MagicMock()
        mock_proc.communicate.return_value = ('4 packets received', '')

        with mock.patch('subprocess.Popen', return_value=mock_proc) as patched_popen:
            resp = self.client.get('/ping/')

        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'10.0.0.1', resp.data)
        self.assertIn(b'4 packets received', resp.data)
        patched_popen.assert_called_once()

    def test_host_in_url_overrides_env(self):
        """Host in URL takes precedence over env var."""
        os.environ['PING_TARGET'] = '10.0.0.1'
        mock_proc = mock.MagicMock()
        mock_proc.communicate.return_value = ('4 packets received', '')

        with mock.patch('subprocess.Popen', return_value=mock_proc):
            resp = self.client.get('/ping/8.8.8.8/')

        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'8.8.8.8', resp.data)
        self.assertNotIn(b'10.0.0.1', resp.data)

    def test_target_env_var_fallback(self):
        """Lowercase 'target' env var works as fallback."""
        os.environ['target'] = '192.168.1.1'
        mock_proc = mock.MagicMock()
        mock_proc.communicate.return_value = ('4 packets received', '')

        with mock.patch('subprocess.Popen', return_value=mock_proc):
            resp = self.client.get('/ping/')

        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'192.168.1.1', resp.data)


if __name__ == '__main__':
    unittest.main()
