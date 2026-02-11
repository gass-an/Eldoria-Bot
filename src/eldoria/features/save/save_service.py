"""Service métier regroupant les opérations de sauvegarde et de maintenance de la base de données, notamment les backups et l'initialisation du schéma."""

from dataclasses import dataclass

from eldoria.db import connection, maintenance, schema


@dataclass(slots=True)
class SaveService:
    """Service métier regroupant les opérations de sauvegarde et de maintenance de la base de données, notamment les backups et l'initialisation du schéma."""

    def get_db_path(self) -> str:
        """Retourne le chemin du fichier de base de données SQLite utilisé par le bot."""
        return connection.DB_PATH
    
    def backup_to_file(self, dst_path: str) -> None:
        """Crée une sauvegarde de la base de données actuelle dans un fichier à l'emplacement spécifié."""
        return maintenance.backup_to_file(dst_path)
    
    def replace_db_file(self, new_db_path: str) -> None:
        """Remplace le fichier de base de données actuel par un nouveau fichier de base de données (par exemple pour restaurer une sauvegarde)."""
        return maintenance.replace_db_file(new_db_path)
    
    def init_db(self) -> None:
        """Initialise le schéma de la base de données en créant les tables nécessaires si elles n'existent pas déjà."""
        return schema.init_db()