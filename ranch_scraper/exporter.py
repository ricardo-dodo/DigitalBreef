import csv
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from .utils import generate_filename, sanitize_filename, clean_table_data

class DynamicExporter:

    def __init__(self):
        self.supported_formats = ['csv', 'json']

    def export_to_csv(self, data: List[Dict[str, Any]], filename: Optional[str]=None) -> str:
        if not data:
            print('No data to export')
            return ''
        cleaned_data = clean_table_data(data)
        if not filename:
            filename = generate_filename('ranch_results', 'csv')
        else:
            filename = sanitize_filename(filename)
            if not filename.endswith('.csv'):
                filename += '.csv'
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                if cleaned_data:
                    fieldnames = list(cleaned_data[0].keys())
                else:
                    fieldnames = []
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for row in cleaned_data:
                    writer.writerow(row)
            print(f'Results exported to {filename}')
            return filename
        except Exception as e:
            print(f'Error exporting to CSV: {e}')
            return ''

    def export_to_json(self, data: List[Dict[str, Any]], filename: Optional[str]=None) -> str:
        if not data:
            print('No data to export')
            return ''
        cleaned_data = clean_table_data(data)
        if not filename:
            filename = generate_filename('ranch_results', 'json')
        else:
            filename = sanitize_filename(filename)
            if not filename.endswith('.json'):
                filename += '.json'
        try:
            with open(filename, 'w', encoding='utf-8') as jsonfile:
                json.dump(cleaned_data, jsonfile, indent=2, ensure_ascii=False)
            print(f'Results exported to {filename}')
            return filename
        except Exception as e:
            print(f'Error exporting to JSON: {e}')
            return ''

    def export_data(self, data: List[Dict[str, Any]], format_type: str, filename: Optional[str]=None) -> str:
        format_type = format_type.lower()
        if format_type not in self.supported_formats:
            print(f'Unsupported format: {format_type}. Supported formats: {self.supported_formats}')
            return ''
        if format_type == 'csv':
            return self.export_to_csv(data, filename)
        elif format_type == 'json':
            return self.export_to_json(data, filename)
        else:
            print(f'Unknown format: {format_type}')
            return ''

    def get_export_info(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not data:
            return {'row_count': 0, 'columns': [], 'sample_data': {}, 'exportable': False}
        columns = list(data[0].keys()) if data else []
        column_types = {}
        for col in columns:
            values = [row.get(col, '') for row in data]
            non_empty = [v for v in values if v]
            if non_empty:
                try:
                    [float(v) for v in non_empty]
                    column_types[col] = 'numeric'
                except ValueError:
                    if all((len(str(v)) <= 10 for v in non_empty)):
                        column_types[col] = 'code'
                    else:
                        column_types[col] = 'text'
            else:
                column_types[col] = 'empty'
        return {'row_count': len(data), 'columns': columns, 'column_types': column_types, 'sample_data': data[0] if data else {}, 'exportable': True}

    def validate_export_format(self, format_type: str) -> bool:
        return format_type.lower() in self.supported_formats

    def get_supported_formats(self) -> List[str]:
        return self.supported_formats.copy()

    def preview_export(self, data: List[Dict[str, Any]], format_type: str, max_rows: int=5) -> str:
        if not data:
            return 'No data to preview'
        preview_data = data[:max_rows]
        if format_type.lower() == 'csv':
            return self._preview_csv(preview_data)
        elif format_type.lower() == 'json':
            return self._preview_json(preview_data)
        else:
            return f'Unsupported format: {format_type}'

    def _preview_csv(self, data: List[Dict[str, Any]]) -> str:
        if not data:
            return 'No data'
        lines = []
        headers = list(data[0].keys())
        lines.append(','.join(headers))
        for row in data:
            values = [str(row.get(h, '')) for h in headers]
            lines.append(','.join(values))
        return '\n'.join(lines)

    def _preview_json(self, data: List[Dict[str, Any]]) -> str:
        return json.dumps(data, indent=2, ensure_ascii=False)

    def export_with_metadata(self, data: List[Dict[str, Any]], format_type: str, filename: Optional[str]=None) -> str:
        if not data:
            print('No data to export')
            return ''
        metadata = {'export_timestamp': datetime.now().isoformat(), 'total_records': len(data), 'columns': list(data[0].keys()) if data else [], 'source': 'ranch_scraper'}
        if format_type.lower() == 'json':
            export_data = {'metadata': metadata, 'data': data}
            if not filename:
                filename = generate_filename('ranch_results', 'json')
            else:
                filename = sanitize_filename(filename)
                if not filename.endswith('.json'):
                    filename += '.json'
            try:
                with open(filename, 'w', encoding='utf-8') as jsonfile:
                    json.dump(export_data, jsonfile, indent=2, ensure_ascii=False)
                print(f'Results exported to {filename}')
                return filename
            except Exception as e:
                print(f'Error exporting to JSON: {e}')
                return ''
        else:
            data_file = self.export_data(data, format_type, filename)
            if data_file:
                metadata_filename = data_file.replace('.csv', '_metadata.json')
                try:
                    with open(metadata_filename, 'w', encoding='utf-8') as metafile:
                        json.dump(metadata, metafile, indent=2, ensure_ascii=False)
                    print(f'Metadata exported to {metadata_filename}')
                except Exception as e:
                    print(f'Error exporting metadata: {e}')
            return data_file
