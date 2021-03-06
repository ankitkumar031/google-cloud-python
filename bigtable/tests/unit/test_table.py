# Copyright 2015 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import unittest

import mock


class Test___mutate_rows_request(unittest.TestCase):

    def _call_fut(self, table_name, rows):
        from google.cloud.bigtable.table import _mutate_rows_request

        return _mutate_rows_request(table_name, rows)

    @mock.patch('google.cloud.bigtable.table._MAX_BULK_MUTATIONS', new=3)
    def test__mutate_rows_too_many_mutations(self):
        from google.cloud.bigtable.row import DirectRow
        from google.cloud.bigtable.table import TooManyMutationsError

        table = mock.Mock(name='table', spec=['name'])
        table.name = 'table'
        rows = [DirectRow(row_key=b'row_key', table=table),
                DirectRow(row_key=b'row_key_2', table=table)]
        rows[0].set_cell('cf1', b'c1', 1)
        rows[0].set_cell('cf1', b'c1', 2)
        rows[1].set_cell('cf1', b'c1', 3)
        rows[1].set_cell('cf1', b'c1', 4)
        with self.assertRaises(TooManyMutationsError):
            self._call_fut('table', rows)

    def test__mutate_rows_request(self):
        from google.cloud.bigtable.row import DirectRow

        table = mock.Mock(name='table', spec=['name'])
        table.name = 'table'
        rows = [DirectRow(row_key=b'row_key', table=table),
                DirectRow(row_key=b'row_key_2', table=table)]
        rows[0].set_cell('cf1', b'c1', b'1')
        rows[1].set_cell('cf1', b'c1', b'2')
        result = self._call_fut('table', rows)

        expected_result = _mutate_rows_request_pb(table_name='table')
        entry1 = expected_result.entries.add()
        entry1.row_key = b'row_key'
        mutations1 = entry1.mutations.add()
        mutations1.set_cell.family_name = 'cf1'
        mutations1.set_cell.column_qualifier = b'c1'
        mutations1.set_cell.timestamp_micros = -1
        mutations1.set_cell.value = b'1'
        entry2 = expected_result.entries.add()
        entry2.row_key = b'row_key_2'
        mutations2 = entry2.mutations.add()
        mutations2.set_cell.family_name = 'cf1'
        mutations2.set_cell.column_qualifier = b'c1'
        mutations2.set_cell.timestamp_micros = -1
        mutations2.set_cell.value = b'2'

        self.assertEqual(result, expected_result)


class Test__check_row_table_name(unittest.TestCase):

    def _call_fut(self, table_name, row):
        from google.cloud.bigtable.table import _check_row_table_name

        return _check_row_table_name(table_name, row)

    def test_wrong_table_name(self):
        from google.cloud.bigtable.table import TableMismatchError
        from google.cloud.bigtable.row import DirectRow

        table = mock.Mock(name='table', spec=['name'])
        table.name = 'table'
        row = DirectRow(row_key=b'row_key', table=table)
        with self.assertRaises(TableMismatchError):
            self._call_fut('other_table', row)

    def test_right_table_name(self):
        from google.cloud.bigtable.row import DirectRow

        table = mock.Mock(name='table', spec=['name'])
        table.name = 'table'
        row = DirectRow(row_key=b'row_key', table=table)
        result = self._call_fut('table', row)
        self.assertFalse(result)


class Test__check_row_type(unittest.TestCase):
    def _call_fut(self, row):
        from google.cloud.bigtable.table import _check_row_type

        return _check_row_type(row)

    def test_test_wrong_row_type(self):
        from google.cloud.bigtable.row import ConditionalRow

        row = ConditionalRow(row_key=b'row_key', table='table', filter_=None)
        with self.assertRaises(TypeError):
            self._call_fut(row)

    def test_right_row_type(self):
        from google.cloud.bigtable.row import DirectRow

        row = DirectRow(row_key=b'row_key', table='table')
        result = self._call_fut(row)
        self.assertFalse(result)


class TestTable(unittest.TestCase):

    PROJECT_ID = 'project-id'
    INSTANCE_ID = 'instance-id'
    INSTANCE_NAME = ('projects/' + PROJECT_ID + '/instances/' + INSTANCE_ID)
    TABLE_ID = 'table-id'
    TABLE_NAME = INSTANCE_NAME + '/tables/' + TABLE_ID
    ROW_KEY = b'row-key'
    FAMILY_NAME = u'family'
    QUALIFIER = b'qualifier'
    TIMESTAMP_MICROS = 100
    VALUE = b'value'

    @staticmethod
    def _get_target_class():
        from google.cloud.bigtable.table import Table

        return Table

    def _make_one(self, *args, **kwargs):
        return self._get_target_class()(*args, **kwargs)

    def test_constructor(self):
        table_id = 'table-id'
        instance = object()

        table = self._make_one(table_id, instance)
        self.assertEqual(table.table_id, table_id)
        self.assertIs(table._instance, instance)

    def test_name_property(self):
        table_id = 'table-id'
        instance_name = 'instance_name'

        instance = _Instance(instance_name)
        table = self._make_one(table_id, instance)
        expected_name = instance_name + '/tables/' + table_id
        self.assertEqual(table.name, expected_name)

    def test_column_family_factory(self):
        from google.cloud.bigtable.column_family import ColumnFamily

        table_id = 'table-id'
        gc_rule = object()
        table = self._make_one(table_id, None)
        column_family_id = 'column_family_id'
        column_family = table.column_family(column_family_id, gc_rule=gc_rule)

        self.assertIsInstance(column_family, ColumnFamily)
        self.assertEqual(column_family.column_family_id, column_family_id)
        self.assertIs(column_family.gc_rule, gc_rule)
        self.assertEqual(column_family._table, table)

    def test_row_factory_direct(self):
        from google.cloud.bigtable.row import DirectRow

        table_id = 'table-id'
        table = self._make_one(table_id, None)
        row_key = b'row_key'
        row = table.row(row_key)

        self.assertIsInstance(row, DirectRow)
        self.assertEqual(row._row_key, row_key)
        self.assertEqual(row._table, table)

    def test_row_factory_conditional(self):
        from google.cloud.bigtable.row import ConditionalRow

        table_id = 'table-id'
        table = self._make_one(table_id, None)
        row_key = b'row_key'
        filter_ = object()
        row = table.row(row_key, filter_=filter_)

        self.assertIsInstance(row, ConditionalRow)
        self.assertEqual(row._row_key, row_key)
        self.assertEqual(row._table, table)

    def test_row_factory_append(self):
        from google.cloud.bigtable.row import AppendRow

        table_id = 'table-id'
        table = self._make_one(table_id, None)
        row_key = b'row_key'
        row = table.row(row_key, append=True)

        self.assertIsInstance(row, AppendRow)
        self.assertEqual(row._row_key, row_key)
        self.assertEqual(row._table, table)

    def test_row_factory_failure(self):
        table = self._make_one(self.TABLE_ID, None)
        with self.assertRaises(ValueError):
            table.row(b'row_key', filter_=object(), append=True)

    def test___eq__(self):
        instance = object()
        table1 = self._make_one(self.TABLE_ID, instance)
        table2 = self._make_one(self.TABLE_ID, instance)
        self.assertEqual(table1, table2)

    def test___eq__type_differ(self):
        table1 = self._make_one(self.TABLE_ID, None)
        table2 = object()
        self.assertNotEqual(table1, table2)

    def test___ne__same_value(self):
        instance = object()
        table1 = self._make_one(self.TABLE_ID, instance)
        table2 = self._make_one(self.TABLE_ID, instance)
        comparison_val = (table1 != table2)
        self.assertFalse(comparison_val)

    def test___ne__(self):
        table1 = self._make_one('table_id1', 'instance1')
        table2 = self._make_one('table_id2', 'instance2')
        self.assertNotEqual(table1, table2)

    def _create_test_helper(self, initial_split_keys, column_families=()):
        from google.cloud._helpers import _to_bytes
        from tests.unit._testing import _FakeStub

        client = _Client()
        instance = _Instance(self.INSTANCE_NAME, client=client)
        table = self._make_one(self.TABLE_ID, instance)

        # Create request_pb
        splits_pb = [
            _CreateTableRequestSplitPB(key=_to_bytes(key))
            for key in initial_split_keys or ()]
        table_pb = None
        if column_families:
            table_pb = _TablePB()
            for cf in column_families:
                cf_pb = table_pb.column_families[cf.column_family_id]
                if cf.gc_rule is not None:
                    cf_pb.gc_rule.MergeFrom(cf.gc_rule.to_pb())
        request_pb = _CreateTableRequestPB(
            initial_splits=splits_pb,
            parent=self.INSTANCE_NAME,
            table_id=self.TABLE_ID,
            table=table_pb,
        )

        # Create response_pb
        response_pb = _TablePB()

        # Patch the stub used by the API method.
        client._table_stub = stub = _FakeStub(response_pb)

        # Create expected_result.
        expected_result = None  # create() has no return value.

        # Perform the method and check the result.
        result = table.create(initial_split_keys=initial_split_keys,
                              column_families=column_families)
        self.assertEqual(result, expected_result)
        self.assertEqual(stub.method_calls, [(
            'CreateTable',
            (request_pb,),
            {},
        )])

    def test_create(self):
        initial_split_keys = None
        self._create_test_helper(initial_split_keys)

    def test_create_with_split_keys(self):
        initial_split_keys = [b's1', b's2']
        self._create_test_helper(initial_split_keys)

    def test_create_with_column_families(self):
        from google.cloud.bigtable.column_family import ColumnFamily
        from google.cloud.bigtable.column_family import MaxVersionsGCRule

        cf_id1 = 'col-fam-id1'
        cf1 = ColumnFamily(cf_id1, None)
        cf_id2 = 'col-fam-id2'
        gc_rule = MaxVersionsGCRule(42)
        cf2 = ColumnFamily(cf_id2, None, gc_rule=gc_rule)

        initial_split_keys = None
        column_families = [cf1, cf2]
        self._create_test_helper(initial_split_keys,
                                 column_families=column_families)

    def _list_column_families_helper(self):
        from tests.unit._testing import _FakeStub

        client = _Client()
        instance = _Instance(self.INSTANCE_NAME, client=client)
        table = self._make_one(self.TABLE_ID, instance)

        # Create request_pb
        request_pb = _GetTableRequestPB(name=self.TABLE_NAME)

        # Create response_pb
        COLUMN_FAMILY_ID = 'foo'
        column_family = _ColumnFamilyPB()
        response_pb = _TablePB(
            column_families={COLUMN_FAMILY_ID: column_family},
        )

        # Patch the stub used by the API method.
        client._table_stub = stub = _FakeStub(response_pb)

        # Create expected_result.
        expected_result = {
            COLUMN_FAMILY_ID: table.column_family(COLUMN_FAMILY_ID),
        }

        # Perform the method and check the result.
        result = table.list_column_families()
        self.assertEqual(result, expected_result)
        self.assertEqual(stub.method_calls, [(
            'GetTable',
            (request_pb,),
            {},
        )])

    def test_list_column_families(self):
        self._list_column_families_helper()

    def test_delete(self):
        from google.protobuf import empty_pb2
        from tests.unit._testing import _FakeStub

        client = _Client()
        instance = _Instance(self.INSTANCE_NAME, client=client)
        table = self._make_one(self.TABLE_ID, instance)

        # Create request_pb
        request_pb = _DeleteTableRequestPB(name=self.TABLE_NAME)

        # Create response_pb
        response_pb = empty_pb2.Empty()

        # Patch the stub used by the API method.
        client._table_stub = stub = _FakeStub(response_pb)

        # Create expected_result.
        expected_result = None  # delete() has no return value.

        # Perform the method and check the result.
        result = table.delete()
        self.assertEqual(result, expected_result)
        self.assertEqual(stub.method_calls, [(
            'DeleteTable',
            (request_pb,),
            {},
        )])

    def _read_row_helper(self, chunks, expected_result):
        from google.cloud._testing import _Monkey
        from tests.unit._testing import _FakeStub
        from google.cloud.bigtable import table as MUT

        client = _Client()
        instance = _Instance(self.INSTANCE_NAME, client=client)
        table = self._make_one(self.TABLE_ID, instance)

        # Create request_pb
        request_pb = object()  # Returned by our mock.
        mock_created = []

        def mock_create_row_request(table_name, row_key, filter_):
            mock_created.append((table_name, row_key, filter_))
            return request_pb

        # Create response_iterator
        if chunks is None:
            response_iterator = iter(())  # no responses at all
        else:
            response_pb = _ReadRowsResponsePB(chunks=chunks)
            response_iterator = iter([response_pb])

        # Patch the stub used by the API method.
        client._data_stub = stub = _FakeStub(response_iterator)

        # Perform the method and check the result.
        filter_obj = object()
        with _Monkey(MUT, _create_row_request=mock_create_row_request):
            result = table.read_row(self.ROW_KEY, filter_=filter_obj)

        self.assertEqual(result, expected_result)
        self.assertEqual(stub.method_calls, [(
            'ReadRows',
            (request_pb,),
            {},
        )])
        self.assertEqual(mock_created,
                         [(table.name, self.ROW_KEY, filter_obj)])

    def test_read_row_miss_no__responses(self):
        self._read_row_helper(None, None)

    def test_read_row_miss_no_chunks_in_response(self):
        chunks = []
        self._read_row_helper(chunks, None)

    def test_read_row_complete(self):
        from google.cloud.bigtable.row_data import Cell
        from google.cloud.bigtable.row_data import PartialRowData

        chunk = _ReadRowsResponseCellChunkPB(
            row_key=self.ROW_KEY,
            family_name=self.FAMILY_NAME,
            qualifier=self.QUALIFIER,
            timestamp_micros=self.TIMESTAMP_MICROS,
            value=self.VALUE,
            commit_row=True,
        )
        chunks = [chunk]
        expected_result = PartialRowData(row_key=self.ROW_KEY)
        family = expected_result._cells.setdefault(self.FAMILY_NAME, {})
        column = family.setdefault(self.QUALIFIER, [])
        column.append(Cell.from_pb(chunk))
        self._read_row_helper(chunks, expected_result)

    def test_read_row_still_partial(self):
        chunk = _ReadRowsResponseCellChunkPB(
            row_key=self.ROW_KEY,
            family_name=self.FAMILY_NAME,
            qualifier=self.QUALIFIER,
            timestamp_micros=self.TIMESTAMP_MICROS,
            value=self.VALUE,
        )
        # No "commit row".
        chunks = [chunk]
        with self.assertRaises(ValueError):
            self._read_row_helper(chunks, None)

    def test_mutate_rows(self):
        from google.cloud.bigtable._generated.bigtable_pb2 import (
            MutateRowsResponse)
        from google.cloud.bigtable.row import DirectRow
        from google.rpc.status_pb2 import Status
        from tests.unit._testing import _FakeStub

        client = _Client()
        instance = _Instance(self.INSTANCE_NAME, client=client)
        table = self._make_one(self.TABLE_ID, instance)

        row_1 = DirectRow(row_key=b'row_key', table=table)
        row_1.set_cell('cf', b'col', b'value1')
        row_2 = DirectRow(row_key=b'row_key_2', table=table)
        row_2.set_cell('cf', b'col', b'value2')

        response = MutateRowsResponse(
            entries=[
                MutateRowsResponse.Entry(
                    index=0,
                    status=Status(code=0),
                ),
                MutateRowsResponse.Entry(
                    index=1,
                    status=Status(code=1),
                ),
            ],
        )

        # Patch the stub used by the API method.
        client._data_stub = _FakeStub([response])
        statuses = table.mutate_rows([row_1, row_2])
        result = [status.code for status in statuses]
        expected_result = [0, 1]

        self.assertEqual(result, expected_result)


    def test_read_rows(self):
        from google.cloud._testing import _Monkey
        from tests.unit._testing import _FakeStub
        from google.cloud.bigtable.row_data import PartialRowsData
        from google.cloud.bigtable import table as MUT

        client = _Client()
        instance = _Instance(self.INSTANCE_NAME, client=client)
        table = self._make_one(self.TABLE_ID, instance)

        # Create request_pb
        request_pb = object()  # Returned by our mock.
        mock_created = []

        def mock_create_row_request(table_name, **kwargs):
            mock_created.append((table_name, kwargs))
            return request_pb

        # Create response_iterator
        response_iterator = object()

        # Patch the stub used by the API method.
        client._data_stub = stub = _FakeStub(response_iterator)

        # Create expected_result.
        expected_result = PartialRowsData(response_iterator)

        # Perform the method and check the result.
        start_key = b'start-key'
        end_key = b'end-key'
        filter_obj = object()
        limit = 22
        with _Monkey(MUT, _create_row_request=mock_create_row_request):
            result = table.read_rows(
                start_key=start_key, end_key=end_key, filter_=filter_obj,
                limit=limit)

        self.assertEqual(result, expected_result)
        self.assertEqual(stub.method_calls, [(
            'ReadRows',
            (request_pb,),
            {},
        )])
        created_kwargs = {
            'start_key': start_key,
            'end_key': end_key,
            'filter_': filter_obj,
            'limit': limit,
        }
        self.assertEqual(mock_created, [(table.name, created_kwargs)])

    def test_sample_row_keys(self):
        from tests.unit._testing import _FakeStub

        client = _Client()
        instance = _Instance(self.INSTANCE_NAME, client=client)
        table = self._make_one(self.TABLE_ID, instance)

        # Create request_pb
        request_pb = _SampleRowKeysRequestPB(table_name=self.TABLE_NAME)

        # Create response_iterator
        response_iterator = object()  # Just passed to a mock.

        # Patch the stub used by the API method.
        client._data_stub = stub = _FakeStub(response_iterator)

        # Create expected_result.
        expected_result = response_iterator

        # Perform the method and check the result.
        result = table.sample_row_keys()
        self.assertEqual(result, expected_result)
        self.assertEqual(stub.method_calls, [(
            'SampleRowKeys',
            (request_pb,),
            {},
        )])


class Test__create_row_request(unittest.TestCase):

    def _call_fut(self, table_name, row_key=None, start_key=None, end_key=None,
                  filter_=None, limit=None):
        from google.cloud.bigtable.table import _create_row_request

        return _create_row_request(
            table_name, row_key=row_key, start_key=start_key, end_key=end_key,
            filter_=filter_, limit=limit)

    def test_table_name_only(self):
        table_name = 'table_name'
        result = self._call_fut(table_name)
        expected_result = _ReadRowsRequestPB(
            table_name=table_name)
        self.assertEqual(result, expected_result)

    def test_row_key_row_range_conflict(self):
        with self.assertRaises(ValueError):
            self._call_fut(None, row_key=object(), end_key=object())

    def test_row_key(self):
        table_name = 'table_name'
        row_key = b'row_key'
        result = self._call_fut(table_name, row_key=row_key)
        expected_result = _ReadRowsRequestPB(
            table_name=table_name,
        )
        expected_result.rows.row_keys.append(row_key)
        self.assertEqual(result, expected_result)

    def test_row_range_start_key(self):
        table_name = 'table_name'
        start_key = b'start_key'
        result = self._call_fut(table_name, start_key=start_key)
        expected_result = _ReadRowsRequestPB(table_name=table_name)
        expected_result.rows.row_ranges.add(start_key_closed=start_key)
        self.assertEqual(result, expected_result)

    def test_row_range_end_key(self):
        table_name = 'table_name'
        end_key = b'end_key'
        result = self._call_fut(table_name, end_key=end_key)
        expected_result = _ReadRowsRequestPB(table_name=table_name)
        expected_result.rows.row_ranges.add(end_key_open=end_key)
        self.assertEqual(result, expected_result)

    def test_row_range_both_keys(self):
        table_name = 'table_name'
        start_key = b'start_key'
        end_key = b'end_key'
        result = self._call_fut(table_name, start_key=start_key,
                                end_key=end_key)
        expected_result = _ReadRowsRequestPB(table_name=table_name)
        expected_result.rows.row_ranges.add(
            start_key_closed=start_key, end_key_open=end_key)
        self.assertEqual(result, expected_result)

    def test_with_filter(self):
        from google.cloud.bigtable.row_filters import RowSampleFilter

        table_name = 'table_name'
        row_filter = RowSampleFilter(0.33)
        result = self._call_fut(table_name, filter_=row_filter)
        expected_result = _ReadRowsRequestPB(
            table_name=table_name,
            filter=row_filter.to_pb(),
        )
        self.assertEqual(result, expected_result)

    def test_with_limit(self):
        table_name = 'table_name'
        limit = 1337
        result = self._call_fut(table_name, limit=limit)
        expected_result = _ReadRowsRequestPB(
            table_name=table_name,
            rows_limit=limit,
        )
        self.assertEqual(result, expected_result)


def _CreateTableRequestPB(*args, **kw):
    from google.cloud.bigtable._generated import (
        bigtable_table_admin_pb2 as table_admin_v2_pb2)

    return table_admin_v2_pb2.CreateTableRequest(*args, **kw)


def _CreateTableRequestSplitPB(*args, **kw):
    from google.cloud.bigtable._generated import (
        bigtable_table_admin_pb2 as table_admin_v2_pb2)

    return table_admin_v2_pb2.CreateTableRequest.Split(*args, **kw)


def _DeleteTableRequestPB(*args, **kw):
    from google.cloud.bigtable._generated import (
        bigtable_table_admin_pb2 as table_admin_v2_pb2)

    return table_admin_v2_pb2.DeleteTableRequest(*args, **kw)


def _GetTableRequestPB(*args, **kw):
    from google.cloud.bigtable._generated import (
        bigtable_table_admin_pb2 as table_admin_v2_pb2)

    return table_admin_v2_pb2.GetTableRequest(*args, **kw)


def _ReadRowsRequestPB(*args, **kw):
    from google.cloud.bigtable._generated import (
        bigtable_pb2 as messages_v2_pb2)

    return messages_v2_pb2.ReadRowsRequest(*args, **kw)


def _ReadRowsResponseCellChunkPB(*args, **kw):
    from google.cloud.bigtable._generated import (
        bigtable_pb2 as messages_v2_pb2)

    family_name = kw.pop('family_name')
    qualifier = kw.pop('qualifier')
    message = messages_v2_pb2.ReadRowsResponse.CellChunk(*args, **kw)
    message.family_name.value = family_name
    message.qualifier.value = qualifier
    return message


def _ReadRowsResponsePB(*args, **kw):
    from google.cloud.bigtable._generated import (
        bigtable_pb2 as messages_v2_pb2)

    return messages_v2_pb2.ReadRowsResponse(*args, **kw)


def _SampleRowKeysRequestPB(*args, **kw):
    from google.cloud.bigtable._generated import (
        bigtable_pb2 as messages_v2_pb2)

    return messages_v2_pb2.SampleRowKeysRequest(*args, **kw)


def _mutate_rows_request_pb(*args, **kw):
    from google.cloud.bigtable._generated import (
        bigtable_pb2 as data_messages_v2_pb2)

    return data_messages_v2_pb2.MutateRowsRequest(*args, **kw)


def _TablePB(*args, **kw):
    from google.cloud.bigtable._generated import (
        table_pb2 as table_v2_pb2)

    return table_v2_pb2.Table(*args, **kw)


def _ColumnFamilyPB(*args, **kw):
    from google.cloud.bigtable._generated import (
        table_pb2 as table_v2_pb2)

    return table_v2_pb2.ColumnFamily(*args, **kw)


class _Client(object):

    data_stub = None
    instance_stub = None
    operations_stub = None
    table_stub = None


class _Instance(object):

    def __init__(self, name, client=None):
        self.name = name
        self._client = client
