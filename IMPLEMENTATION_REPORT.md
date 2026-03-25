# Internship Task Implementation Report - Movie Booking System

This document provides justifications for the key architectural and performance decisions made during the implementation of the Movie Booking System.

## 1. Scalable Genre and Language Filtering
**Decision:** Implemented server-side faceted filtering with optimized database queries.
- **Query Optimization:** Used `Movie.objects.annotate(has_shows=Exists(...))` to efficiently determine movie availability without expensive joins.
- **Indexing:** Applied composite indexes on `(genre, language)`, `(genre, release_date)`, and `(rating)` in the `Movie` model to avoid full-table scans.
- **Scalability:** Faceted counts are calculated using `values().annotate(count=Count('id'))`, allowing the database to perform the heavy lifting. This strategy supports catalogs of 5,000+ movies by ensuring most filter combinations result in index-only or index-assisted scans.
- **Trade-off:** We prioritized query speed over filter flexibility by using fixed columns for genre and language instead of a more generic EAV (Entity-Attribute-Value) pattern.

## 2. Automated Ticket Email Confirmation
**Decision:** Database-backed non-blocking delivery queue.
- **Background Processing:** Used a `threading.Thread` mechanism to trigger email delivery immediately after booking without blocking the UI response. 
- **Reliability:** Delivery state is persisted in the `EmailDelivery` model. If a network error occurs, the system uses retry logic with exponential backoff.
- **Security:** Emails use standardized Django templates to prevent data leakage. Sensitive payment tokens are never included in the email body.

## 3. Secure YouTube Trailer Embedding
**Decision:** Sanitized embedding with lazy loading.
- **Security:** Implemented a backend validation utility (`get_embed_url`) that parses YouTube URLs using strict regex/parsing to prevent XSS and malicious script injection.
- **Performance:** Used the native HTML `loading="lazy"` attribute and `modestbranding=1` to minimize the performance impact on page speed.

## 4. Payment Gateway Integration
**Decision:** Webhook-first verification with idempotency.
- **Idempotency:** Utilized `idempotency_key` logic in the `Booking` model to ensure that multiple calls from a payment provider for the same transaction do not result in duplicate tickets.
- **Security:** Payment status is updated only through server-side verification of provider signatures, preventing "client-side-only" confirmation fraud.

## 5. Concurrency-Safe Seat Reservation
**Decision:** Row-level pessimistic locking.
- **Race Condition Prevention:** Used `select_for_update()` inside a `transaction.atomic()` block during seat selection. This ensures that if two users select the same seat within milliseconds, the database locks the row for the first requester.
- **Auto-Timeout:** Implemented a background cleanup utility (`release_expired_locks`) that is triggered on every layout refresh, ensuring expired 2-minute locks are freed automatically.

## 6. Advanced Admin Analytics Dashboard
**Decision:** Database-level aggregations with caching.
- **Performance:** Used Django's aggregation functions (`Sum`, `Count`, `ExtractHour`) to perform calculations entirely within the database engine.
- **Efficiency:** Implemented `django.core.cache` to store the dashboard results for 5 minutes, significantly reducing the load on the database.
- **Security:** Strictly enforced `@staff_member_required` to restrict access to authorized personnel only.

**Admin Credentials:**
- **Username:** `admin`
- **Password:** `admin123`
