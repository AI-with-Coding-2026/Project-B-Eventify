# Eventify Base Template — Block Reference Guide

This guide documents all the extendable blocks available in `templates/base.html`.
Every page template should start with `{% extends 'base.html' %}` and override
the blocks it needs.

---

## Quick Start

```html
{% extends 'base.html' %}

{% block title %}My Page — Eventify{% endblock %}

{% block content %}
<h1>Hello, Eventify!</h1>
<p>Your page content goes here.</p>
{% endblock %}
```

---

## All Available Blocks

### `title`
**Location:** `<title>` tag in `<head>`
**Default:** `Eventify`

```html
{% block title %}Events List — Eventify{% endblock %}
```

---

### `extra_head`
**Location:** Inside `<head>`, before Bootstrap CSS
**Default:** Empty
**Use for:** Meta descriptions, Open Graph tags, Google Fonts, etc.

```html
{% block extra_head %}
<meta name="description" content="Browse and book upcoming events">
<link href="https://fonts.googleapis.com/css2?family=Inter&display=swap" rel="stylesheet">
{% endblock %}
```

---

### `extra_css`
**Location:** Inside `<head>`, after Bootstrap CSS
**Default:** Empty
**Use for:** Page-specific stylesheets or inline `<style>` blocks

```html
{% block extra_css %}
<link rel="stylesheet" href="{% static 'css/dashboard.css' %}">
{% endblock %}
```

---

### `navbar`
**Location:** Top of `<body>`
**Default:** Bootstrap dark navbar with Eventify branding + Home/Events/About/Contact links
**Use for:** Replacing or removing the navbar entirely

```html
{# Remove navbar on a fullscreen landing page #}
{% block navbar %}{% endblock %}

{# Or replace with a custom transparent navbar #}
{% block navbar %}
<nav class="navbar navbar-expand-lg navbar-light bg-transparent">
    ...custom navbar...
</nav>
{% endblock %}
```

---

### `page_header`
**Location:** Below navbar, above main content
**Default:** Empty
**Use for:** Hero banners, page title sections with backgrounds

```html
{% block page_header %}
<div class="bg-primary text-white py-5 text-center">
    <h1>Upcoming Events</h1>
    <p class="lead">Find something amazing to attend</p>
</div>
{% endblock %}
```

---

### `breadcrumbs`
**Location:** Inside `<main>`, before messages
**Default:** Empty
**Use for:** Breadcrumb navigation on inner pages

```html
{% block breadcrumbs %}
<nav aria-label="breadcrumb">
    <ol class="breadcrumb">
        <li class="breadcrumb-item"><a href="/">Home</a></li>
        <li class="breadcrumb-item"><a href="/events/">Events</a></li>
        <li class="breadcrumb-item active">Concert Night</li>
    </ol>
</nav>
{% endblock %}
```

---

### `messages`
**Location:** Inside `<main>`, before content
**Default:** Auto-renders Django's `messages` framework as Bootstrap dismissible alerts
**Use for:** Override only if you need a completely custom message style

```html
{# Usually you DON'T need to override this — just use Django messages in your view: #}
{# messages.success(request, 'Booking confirmed!') #}
{# It will automatically appear as a green Bootstrap alert. #}
```

---

### `content`
**Location:** Inside `<main>`, inside a Bootstrap row/col
**Default:** Empty — **this is the main block most pages will fill**

```html
{% block content %}
<h1>Events</h1>
<div class="row">
    <div class="col-md-4">Event card 1</div>
    <div class="col-md-4">Event card 2</div>
    <div class="col-md-4">Event card 3</div>
</div>
{% endblock %}
```

---

### `content_class`
**Location:** CSS class on the content column `<div>`
**Default:** `col-12` (full width)
**Use for:** Changing content width when using a sidebar

```html
{# When using a sidebar, shrink content to 9 columns #}
{% block content_class %}col-md-9{% endblock %}
```

---

### `sidebar`
**Location:** Inside `<main>`, next to content in the same row
**Default:** Empty (hidden)
**Use for:** Dashboard navigation, filters, admin panels

```html
{% block content_class %}col-md-9{% endblock %}

{% block content %}
<h1>Organizer Dashboard</h1>
<p>Your events overview...</p>
{% endblock %}

{% block sidebar %}
<div class="col-md-3">
    <div class="list-group">
        <a href="#" class="list-group-item">My Events</a>
        <a href="#" class="list-group-item">Analytics</a>
        <a href="#" class="list-group-item">Settings</a>
    </div>
</div>
{% endblock %}
```

---

### `footer`
**Location:** Bottom of `<body>`, after `<main>`
**Default:** Light background, centered "© 2026 Eventify. All rights reserved."

```html
{% block footer %}
<footer class="bg-dark text-white py-4">
    <div class="container">
        <div class="row">
            <div class="col-md-6">© 2026 Eventify</div>
            <div class="col-md-6 text-end">
                <a href="#" class="text-white">Privacy</a> |
                <a href="#" class="text-white">Terms</a>
            </div>
        </div>
    </div>
</footer>
{% endblock %}
```

---

### `extra_js`
**Location:** Bottom of `<body>`, after Bootstrap JS
**Default:** Empty
**Use for:** Page-specific JavaScript files or inline scripts

```html
{% block extra_js %}
<script src="{% static 'js/booking-form.js' %}"></script>
<script>
    document.addEventListener('DOMContentLoaded', function() {
        // Page-specific initialization
    });
</script>
{% endblock %}
```

---

## Real-World Examples

### Example: Events List Page
```html
{% extends 'base.html' %}

{% block title %}Events — Eventify{% endblock %}

{% block page_header %}
<div class="bg-primary text-white py-5 text-center">
    <h1>Browse Events</h1>
</div>
{% endblock %}

{% block breadcrumbs %}
<nav aria-label="breadcrumb">
    <ol class="breadcrumb">
        <li class="breadcrumb-item"><a href="/">Home</a></li>
        <li class="breadcrumb-item active">Events</li>
    </ol>
</nav>
{% endblock %}

{% block content %}
<div class="row">
    {% for event in events %}
    <div class="col-md-4 mb-4">
        <div class="card">
            <div class="card-body">
                <h5 class="card-title">{{ event.name }}</h5>
                <p class="card-text">{{ event.description }}</p>
                <a href="#" class="btn btn-primary">Book Now</a>
            </div>
        </div>
    </div>
    {% endfor %}
</div>
{% endblock %}
```

### Example: Dashboard Page (with sidebar)
```html
{% extends 'base.html' %}

{% block title %}Dashboard — Eventify{% endblock %}

{% block content_class %}col-md-9{% endblock %}

{% block content %}
<h1>Organizer Dashboard</h1>
<p>Manage your events here.</p>
{% endblock %}

{% block sidebar %}
<div class="col-md-3">
    <div class="list-group">
        <a href="#" class="list-group-item active">Overview</a>
        <a href="#" class="list-group-item">My Events</a>
        <a href="#" class="list-group-item">Bookings</a>
        <a href="#" class="list-group-item">Settings</a>
    </div>
</div>
{% endblock %}
```
