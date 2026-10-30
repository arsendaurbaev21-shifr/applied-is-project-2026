"""Export the actual installed SQL metadata for documentation, without row data."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.install import prepare_env,ROOT
from backend.db import transaction
prepare_env('localhost')
with transaction() as q:
    tables=q.rows("SELECT name FROM sys.tables WHERE schema_id=SCHEMA_ID('dbo') ORDER BY object_id")
    output=[]
    for t in tables:
        name=t['name']
        cols=q.rows('''SELECT c.name,ty.name AS type,c.max_length,c.precision,c.scale,c.is_nullable,c.is_identity,d.definition AS default_value
            FROM sys.columns c JOIN sys.types ty ON ty.user_type_id=c.user_type_id LEFT JOIN sys.default_constraints d ON d.object_id=c.default_object_id
            WHERE c.object_id=OBJECT_ID(?) ORDER BY c.column_id''',('dbo.'+name,))
        fks=q.rows('''SELECT col.name AS column_name,rt.name AS referenced_table,rc.name AS referenced_column,f.delete_referential_action_desc AS on_delete
            FROM sys.foreign_key_columns fc JOIN sys.foreign_keys f ON f.object_id=fc.constraint_object_id
            JOIN sys.columns col ON col.object_id=fc.parent_object_id AND col.column_id=fc.parent_column_id
            JOIN sys.tables rt ON rt.object_id=fc.referenced_object_id JOIN sys.columns rc ON rc.object_id=fc.referenced_object_id AND rc.column_id=fc.referenced_column_id
            WHERE fc.parent_object_id=OBJECT_ID(?)''',('dbo.'+name,))
        indexes=q.rows('''SELECT i.name,i.is_unique,i.is_primary_key,i.filter_definition,c.name AS column_name,ic.is_included_column,ic.key_ordinal
            FROM sys.indexes i JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
            WHERE i.object_id=OBJECT_ID(?) ORDER BY i.index_id,ic.key_ordinal''',('dbo.'+name,))
        checks=q.rows('SELECT name,definition FROM sys.check_constraints WHERE parent_object_id=OBJECT_ID(?)',('dbo.'+name,))
        output.append(dict(name=name,columns=cols,foreign_keys=fks,indexes=indexes,checks=checks))
    (ROOT/'docs/schema.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
print('Exported',len(output),'tables and',sum(len(t['foreign_keys']) for t in output),'foreign keys')
