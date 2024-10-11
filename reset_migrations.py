import os

def reset_migrations():
    # Get all app names
    apps = [name for name in os.listdir('.') if os.path.isdir(name) and not name.startswith('.')]
    
    for app in apps:
        migrations_dir = os.path.join(app, 'migrations')
        if os.path.exists(migrations_dir):
            # Remove all migration files except __init__.py
            for filename in os.listdir(migrations_dir):
                if filename != '__init__.py' and filename.endswith('.py'):
                    os.remove(os.path.join(migrations_dir, filename))
            print(f"Removed migrations for {app}")
        else:
            print(f"No migrations directory found for {app}")

if __name__ == "__main__":
    reset_migrations()
    print("Migration files removed. Now run 'python manage.py makemigrations' and 'python manage.py migrate'")