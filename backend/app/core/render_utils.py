_NAVBAR_TEMPLATE = """<nav class="bg-white shadow-sm border-b border-gray-200">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-16">
            <div class="flex space-x-8">
                <a href="/finanzas/" class="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-900">
                    Finanzas
                </a>
                <a href="/anotaciones/" class="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-500 hover:text-gray-900">
                    Notas
                </a>
                <a href="/eventos/" class="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-500 hover:text-gray-900">
                    Eventos
                </a>
                <a href="/metas/" class="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-500 hover:text-gray-900">
                    Metas
                </a>
            </div>
            <div class="flex items-center space-x-4">
                <a href="/ajustes/" class="text-sm text-gray-500 hover:text-gray-900">
                    Ajustes
                </a>
                <a href="/auth/logout" class="text-sm text-red-600 hover:text-red-800">
                    Salir
                </a>
            </div>
        </div>
    </div>
</nav>"""

_SIDEBAR_TEMPLATE = """<aside class="w-64 bg-white shadow-sm border-r border-gray-200 min-h-screen p-4">
    <nav class="space-y-2">
        <a href="/finanzas/" class="block px-3 py-2 rounded-md text-sm font-medium text-gray-900 bg-gray-100">
            Dashboard
        </a>
        <a href="/finanzas/transacciones/" class="block px-3 py-2 rounded-md text-sm text-gray-600 hover:bg-gray-50">
            Transacciones
        </a>
        <a href="/finanzas/categorias/" class="block px-3 py-2 rounded-md text-sm text-gray-600 hover:bg-gray-50">
            Categorías
        </a>
        <a href="/finanzas/cuentas/" class="block px-3 py-2 rounded-md text-sm text-gray-600 hover:bg-gray-50">
            Cuentas
        </a>
        <a href="/anotaciones/" class="block px-3 py-2 rounded-md text-sm text-gray-600 hover:bg-gray-50">
            Notas
        </a>
        <a href="/eventos/" class="block px-3 py-2 rounded-md text-sm text-gray-600 hover:bg-gray-50">
            Eventos
        </a>
        <a href="/metas/" class="block px-3 py-2 rounded-md text-sm text-gray-600 hover:bg-gray-50">
            Metas
        </a>
    </nav>
</aside>"""


def render_navbar() -> str:
    return _NAVBAR_TEMPLATE


def render_sidebar() -> str:
    return _SIDEBAR_TEMPLATE


def render_page(title: str, content: str, user: dict | None = None) -> str:
    user_display = user.get("name", "Usuario") if user else "Usuario"
    return f"""<!DOCTYPE html>
<html lang="es" class="h-full">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>:root{{--color-primary:#7C3AED;}}</style>
</head>
<body class="bg-gray-100 min-h-screen flex flex-col">
    {render_navbar()}
    <div class="flex flex-1">
        {render_sidebar()}
        <main class="flex-1 p-6">
            <div class="mb-4">
                <span class="text-sm text-gray-500">Bienvenido, {user_display}</span>
            </div>
            {content}
        </main>
    </div>
</body>
</html>"""
