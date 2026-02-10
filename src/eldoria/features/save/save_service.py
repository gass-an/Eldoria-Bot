from dataclasses import dataclass

from eldoria.db import connection, maintenance, schema

@dataclass(slots=True)
class SaveService:
    def get_db_path(self) ->str:
        return connection.DB_PATH
    
    def backup_to_file(dst_path: str) -> None:
        return maintenance.backup_to_file(dst_path)
    
    def replace_db_file(new_db_path: str) -> None:
        return maintenance.replace_db_file(new_db_path)
    
    def init_db() -> None:
        return schema.init_db()