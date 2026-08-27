from decouple import config


def firebase_config(request):
    """Pass Firebase config variables to all templates."""
    return {
        'firebase_api_key': config('FIREBASE_API_KEY', default='your-api-key'),
        'firebase_auth_domain': config('FIREBASE_AUTH_DOMAIN', default='your-project.firebaseapp.com'),
        'firebase_project_id': config('FIREBASE_PROJECT_ID', default='your-project-id'),
        'firebase_storage_bucket': config('FIREBASE_STORAGE_BUCKET', default='your-project.appspot.com'),
        'firebase_messaging_sender_id': config('FIREBASE_MESSAGING_SENDER_ID', default='your-sender-id'),
        'firebase_app_id': config('FIREBASE_APP_ID', default='your-app-id'),
        'firebase_vapid_key': config('FIREBASE_VAPID_KEY', default='your-vapid-key'),
    }
