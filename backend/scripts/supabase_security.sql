-- Run as the role that owns the application tables after Alembic.
-- The application uses a server-only database role and enforces account ownership.
-- Supabase browser roles must have no direct access to travel or session tables.
DO $$
DECLARE tab text;
BEGIN
  FOREACH tab IN ARRAY ARRAY['accounts','login_sessions','search_sessions','trips','import_drafts',
    'checkout_sessions','mail_connections','service_requests','daily_usage','event_receipts',
    'email_deliveries','bookings','preferences','flight_searches','oauth_login_attempts']
  LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', tab);
    EXECUTE format('REVOKE ALL ON TABLE public.%I FROM anon, authenticated', tab);
  END LOOP;
END $$;
