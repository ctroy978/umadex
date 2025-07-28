# Phase 3: Supabase Auth Client Installation

## Backend Installation (Python/FastAPI)

```bash
# Install Supabase Python client
cd backend
pip install supabase

# Or add to requirements.txt:
echo "supabase>=2.0.0" >> requirements.txt
pip install -r requirements.txt
```

## Frontend Installation (React/Next.js)

```bash
# Install Supabase JavaScript client
cd frontend
npm install @supabase/supabase-js @supabase/auth-helpers-react @supabase/auth-helpers-nextjs

# Or with yarn:
yarn add @supabase/supabase-js @supabase/auth-helpers-react @supabase/auth-helpers-nextjs
```

## Environment Variables to Add

Add these to your `.env` files:

```bash
# Already in your .env from Phase 2:
SUPABASE_URL=https://[PROJECT-REF].supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here

# Frontend needs:
NEXT_PUBLIC_SUPABASE_URL=https://[PROJECT-REF].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here
```