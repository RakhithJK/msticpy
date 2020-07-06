# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""datq query test class."""
import unittest
from functools import partial
from pathlib import Path
from typing import Any, Tuple, Union, Optional, Dict

import pandas as pd

from msticpy.data.data_providers import DriverBase, QueryContainer, QueryProvider
from msticpy.data.query_source import QuerySource

from ..unit_test_lib import get_test_data_path


_TEST_DATA = get_test_data_path()


# pylint: disable=protected-access, invalid-name
class UTDataDriver(DriverBase):
    """Test class."""

    _TEST_ATTRIB = "CustomAttrib"

    def __init__(self, **kwargs):
        """Initialize new instance."""
        super().__init__(**kwargs)
        self._kwargs = kwargs
        self._loaded = True
        self._connected = False
        self.public_attribs = {"test": self._TEST_ATTRIB}
        self.svc_queries = {}, ""

    def connect(self, connection_str: Optional[str] = None, **kwargs):
        """Test method."""
        del connection_str
        self._connected = True

    def query(
        self, query: str, query_source: QuerySource = None
    ) -> Union[pd.DataFrame, Any]:
        """Test method."""
        del query_source
        return pd.DataFrame(data=query, index=[0], columns=["query"])

    def query_with_results(self, query: str, **kwargs) -> Tuple[pd.DataFrame, Any]:
        """Test method."""
        return (pd.DataFrame(data=query, index=[0], columns=["query"]), query)

    @property
    def service_queries(self) -> Tuple[Dict[str, str], str]:
        """Return dynamic queries available on connection to service."""
        return self.svc_queries


class TestDataQuery(unittest.TestCase):
    """Unit test class."""

    provider = None

    def setUp(self):
        """Test initialization."""
        provider = UTDataDriver()
        self.assertTrue(provider.loaded)
        provider.connect("testuri")
        self.assertTrue(provider.connected)
        self.provider = provider
        self.la_provider = QueryProvider(
            data_environment="LogAnalytics", driver=self.provider
        )

    def test_load_kql_query_defs(self):
        """Test loading query definitions."""
        la_provider = self.la_provider
        la_provider.connect(connection_str="test")
        self.assertEqual(getattr(la_provider, "test"), "CustomAttrib")

        # Did we read and process the query definitions OK
        q_sources = la_provider._query_store.data_families
        self.assertGreaterEqual(len(q_sources["WindowsSecurity"]), 9)
        self.assertGreaterEqual(len(q_sources["SecurityAlert"]), 5)
        self.assertGreaterEqual(len(q_sources["LinuxSyslog"]), 5)

        # pick one item and check properties
        get_alert_q = q_sources["SecurityAlert"]["get_alert"]
        self.assertEqual(len(get_alert_q.default_params), 7)
        self.assertEqual(len(get_alert_q.params), 8)
        self.assertEqual(len(get_alert_q.required_params), 1)
        self.assertEqual(len(get_alert_q.metadata), 6)
        self.assertIn("data_families", get_alert_q.metadata)
        self.assertIn("data_environments", get_alert_q.metadata)
        self.assertEqual(len(get_alert_q.data_families), 1)
        self.assertEqual(get_alert_q.name, "get_alert")
        self.assertIn("Retrieves", get_alert_q.description)

    def test_query_create_funcs(self):
        """Test create partial functions."""
        la_provider = self.la_provider
        # graph_provider = QueryProvider(data_environment = 'SecurityGraph',
        #                           la_provider     driver='dummy')

        all_queries = [
            q for q in dir(la_provider.all_queries) if not q.startswith("__")
        ]
        winsec_queries = [
            q for q in dir(la_provider.WindowsSecurity) if not q.startswith("__")
        ]
        alert_queries = [
            q for q in dir(la_provider.SecurityAlert) if not q.startswith("__")
        ]
        self.assertGreaterEqual(len(all_queries), 14)
        self.assertGreaterEqual(len(winsec_queries), 9)
        self.assertGreaterEqual(len(alert_queries), 5)

        # Test that function attributes have been created properly
        for _, func in la_provider.all_queries:
            self.assertIsInstance(func, partial)
            self.assertTrue(len(func.__doc__))
            self.assertIn("Parameters", func.__doc__)

    def test_load_query_exec(self):
        """Test run query."""
        la_provider = self.la_provider
        df = la_provider.all_queries.get_alert("help")
        self.assertIsNone(df)

        with self.assertRaises(ValueError) as cm:
            df = la_provider.all_queries.get_alert()
            self.assertIn("system_alert_id", str(cm.exception))

        df = la_provider.all_queries.get_alert(system_alert_id="foo")
        self.assertEqual(len(df), 1)
        self.assertIn('SystemAlertId == "foo"', df["query"].iloc[0])

    def test_load_graph_query_defs(self):
        """Test Security graph query load."""
        provider = QueryProvider(data_environment="SecurityGraph", driver=self.provider)

        # Did we read and process the query definitions OK
        q_sources = provider._query_store.data_families
        self.assertGreaterEqual(len(q_sources["SecurityGraphAlert"]), 7)

        # pick one item and check properties
        get_alert_q = q_sources["SecurityGraphAlert"]["get_alert"]
        self.assertEqual(len(get_alert_q.default_params), 6)
        self.assertEqual(len(get_alert_q.params), 7)
        self.assertEqual(len(get_alert_q.required_params), 1)
        self.assertEqual(len(get_alert_q.metadata), 6)
        self.assertIn("data_families", get_alert_q.metadata)
        self.assertIn("data_environments", get_alert_q.metadata)
        self.assertEqual(len(get_alert_q.data_families), 1)
        self.assertEqual(get_alert_q.name, "get_alert")
        self.assertIn("Retrieves", get_alert_q.description)

    def test_graph_query_create_funcs(self):
        """Test Security Graph create partial functions."""
        provider = QueryProvider(data_environment="SecurityGraph", driver=self.provider)

        all_queries = [q for q in dir(provider.all_queries) if not q.startswith("__")]
        alert_queries = [
            q for q in dir(provider.SecurityGraphAlert) if not q.startswith("__")
        ]
        self.assertGreaterEqual(len(all_queries), 7)
        self.assertGreaterEqual(len(alert_queries), 7)

        # Test that function attributes have been created properly
        for _, func in provider.all_queries:
            self.assertIsInstance(func, partial)
            self.assertTrue(len(func.__doc__))
            self.assertIn("Parameters", func.__doc__)

    def test_graph_load_query_exec(self):
        """Test Security graph run query."""
        provider = QueryProvider(data_environment="SecurityGraph", driver=self.provider)
        df = provider.all_queries.get_alert("help")
        self.assertIsNone(df)

        with self.assertRaises(ValueError) as cm:
            df = provider.all_queries.get_alert()
            self.assertIn("alert_id", str(cm.exception))

        df = provider.all_queries.get_alert(alert_id="foo")
        self.assertEqual(len(df), 1)
        self.assertIn("/foo", df["query"].iloc[0])

    def test_load_yaml_def(self):
        """Test query loader rejecting badly formed query files."""
        la_provider = self.la_provider
        with self.assertRaises((ImportError, ValueError)) as cm:
            file_path = Path(_TEST_DATA, "data_q_meta_fail.yaml")
            la_provider.import_query_file(query_file=file_path)
            self.assertIn("no data families defined", str(cm.exception))

        with self.assertRaises((ImportError, ValueError)) as cm:
            file_path = Path(_TEST_DATA, "data_q_source_fail_param.yaml")
            la_provider.import_query_file(query_file=file_path)
            self.assertIn("Missing parameters are", str(cm.exception))

        with self.assertRaises((ImportError, ValueError)) as cm:
            file_path = Path(_TEST_DATA, "data_q_source_fail_type.yaml")
            la_provider.import_query_file(query_file=file_path)
            self.assertIn("Parameters with missing types", str(cm.exception))

        before_queries = len(list(la_provider.list_queries()))
        file_path = Path(_TEST_DATA, "data_q_success.yaml")
        la_provider.import_query_file(query_file=file_path)

        self.assertEqual(before_queries + 3, len(list(la_provider.list_queries())))

    def test_load_hierchical_q_paths(self):
        """Test use of hierarchical query paths."""
        la_provider = self.la_provider
        file_path = Path(_TEST_DATA, "data_q_hierarchy.yaml")
        la_provider.import_query_file(query_file=file_path)

        self.assertIsNotNone(la_provider.Alerts)
        self.assertEqual(len(la_provider.Alerts), 3)

        for _, item in la_provider.Alerts:
            self.assertTrue(isinstance(item, (partial, QueryContainer)))
            if isinstance(item, QueryContainer):
                self.assertTrue(repr(item).startswith("query"))
                self.assertIn("(query)", repr(item))

        self.assertIsInstance(la_provider.Alerts.type1.query1, partial)
        self.assertIsInstance(la_provider.Alerts.type2.query2, partial)
        self.assertIsInstance(la_provider.Alerts.type3.query3, partial)

    def test_query_store_get(self):
        """Test QueryStore get function."""
        la_provider = self.la_provider
        file_path = Path(_TEST_DATA, "data_q_hierarchy.yaml")
        la_provider.import_query_file(query_file=file_path)
        q_store = la_provider._query_store

        q_src = q_store.get_query("Alerts.type1.query1")
        self.assertIsInstance(q_src, QuerySource)
        self.assertEqual(q_src.name, "query1")
        q_src2 = q_store.get_query("Alerts.type1.query1", query_path="Alerts")
        self.assertIsInstance(q_src2, QuerySource)
        self.assertIs(q_src, q_src2)
        q_src3 = q_store.get_query("type1.query1", query_path="Alerts")
        self.assertIsInstance(q_src3, QuerySource)
        self.assertIs(q_src, q_src3)

        with self.assertRaises(LookupError):
            q_src = q_store.get_query("Alerts.type1.query2")

    def test_query_store_find(self):
        """Test QueryStore find query function."""
        la_provider = self.la_provider
        file_path = Path(_TEST_DATA, "data_q_hierarchy.yaml")
        la_provider.import_query_file(query_file=file_path)
        q_store = la_provider._query_store

        result = list(q_store.find_query("query1"))
        self.assertGreaterEqual(len(result), 1)

        result = list(q_store.find_query("missing_query1"))
        self.assertEqual(len(result), 0)

    def test_connect_queries(self):
        """Test queries provided at connect time."""
        queries = {
            "test_query1": "Select * from test",
            "test_query2": "Select * from test2",
            "test.query3": "Select * from test2",
        }

        ut_provider = UTDataDriver()
        ut_provider.svc_queries = (queries, "SavedSearches")

        data_provider = QueryProvider(
            data_environment="LogAnalytics", driver=ut_provider
        )
        data_provider.connect("testuri")

        # Check that we have expected attributes
        self.assertTrue(hasattr(data_provider, "SavedSearches"))
        saved_searches = getattr(data_provider, "SavedSearches")
        for attr in queries:
            attr = attr.split(".")[0]
            self.assertTrue(hasattr(saved_searches, attr))
            self.assertTrue(
                isinstance(getattr(saved_searches, attr), (partial, QueryContainer))
            )

        # Check that we have expected query text
        q_store = data_provider._query_store
        q_src = q_store.get_query("SavedSearches.test.query3")
        self.assertEqual(q_src.query, queries["test.query3"])

    def test_connect_queries_dotted(self):
        """Test queries provided at connect time."""
        queries = {
            "test_query1": "Select * from test",
            "test_query2": "Select * from test2",
            "test.query3": "Select * from test2",
        }
        # Same test as above but with dotted container
        ut_provider = UTDataDriver()
        ut_provider.svc_queries = (queries, "Saved.Searches")
        data_provider = QueryProvider(
            data_environment="LogAnalytics", driver=ut_provider
        )
        data_provider.connect("testuri")

        self.assertTrue(hasattr(data_provider, "Saved"))
        saved_searches = getattr(data_provider, "Saved")
        saved_searches = getattr(saved_searches, "Searches")
        for attr in queries:
            attr = attr.split(".")[0]
            self.assertTrue(hasattr(saved_searches, attr))
            self.assertTrue(
                isinstance(getattr(saved_searches, attr), (partial, QueryContainer))
            )

        q_store = data_provider._query_store
        q_src = q_store.get_query("Saved.Searches.test.query3")
        self.assertEqual(q_src.query, queries["test.query3"])
