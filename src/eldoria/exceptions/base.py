""""Module contenant la base pour les exceptions personnalisées de l'application Eldoria."""

class AppError(Exception):
    """Classe de base pour les exceptions personnalisées de l'application Eldoria.
    
    Toutes les exceptions spécifiques à l'application devraient hériter de cette classe.
    Cela permet de capturer et de gérer facilement toutes les exceptions personnalisées de l'application en attrapant simplement `AppError`.
    """