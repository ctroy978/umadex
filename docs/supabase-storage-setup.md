# Supabase Storage Setup for UMALecture Images

This guide will help you set up Supabase Storage for handling lecture images.

## 1. Create Storage Bucket

Run this SQL in your Supabase SQL editor:

```sql
-- Create a public bucket for lecture images
INSERT INTO storage.buckets (id, name, public)
VALUES ('lecture-images', 'lecture-images', true);

-- Set up RLS policies for the bucket
CREATE POLICY "Teachers can upload lecture images" ON storage.objects
FOR INSERT WITH CHECK (
    auth.role() = 'authenticated' AND 
    bucket_id = 'lecture-images' AND
    (storage.foldername(name))[1] = 'lectures'
);

CREATE POLICY "Teachers can update their lecture images" ON storage.objects
FOR UPDATE WITH CHECK (
    auth.role() = 'authenticated' AND 
    bucket_id = 'lecture-images' AND
    (storage.foldername(name))[1] = 'lectures'
);

CREATE POLICY "Teachers can delete their lecture images" ON storage.objects
FOR DELETE USING (
    auth.role() = 'authenticated' AND 
    bucket_id = 'lecture-images' AND
    (storage.foldername(name))[1] = 'lectures'
);

-- Public can view all lecture images (since bucket is public)
CREATE POLICY "Public can view lecture images" ON storage.objects
FOR SELECT USING (bucket_id = 'lecture-images');
```

## 2. Update Database Schema

Add the necessary columns to store Supabase Storage references:

```sql
-- Add storage-related columns if they don't exist
ALTER TABLE lecture_images 
ADD COLUMN IF NOT EXISTS storage_path TEXT,
ADD COLUMN IF NOT EXISTS public_url TEXT;

-- Update existing records if migrating from file storage
-- UPDATE lecture_images SET public_url = original_url WHERE public_url IS NULL;
```

## 3. Environment Variables

Make sure these are set in your `.env` files:

```bash
# Frontend (.env.local)
NEXT_PUBLIC_SUPABASE_URL=your-project-url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key

# Backend (.env)
SUPABASE_URL=your-project-url
SUPABASE_SERVICE_KEY=your-service-key
```

## 4. Test the Setup

1. Go to your Supabase dashboard
2. Navigate to Storage
3. You should see a `lecture-images` bucket
4. Try uploading a test image through the dashboard

## 5. Image URL Format

Images will be accessible at:
```
https://[your-project-id].supabase.co/storage/v1/object/public/lecture-images/lectures/[lecture-id]/[filename]
```

## 6. Optional: Image Transformations

Supabase Storage supports on-the-fly image transformations:

```javascript
// Get a thumbnail (200x200)
const thumbnailUrl = `${publicUrl}?width=200&height=200`

// Get a specific quality
const optimizedUrl = `${publicUrl}?quality=80`

// Resize while maintaining aspect ratio
const resizedUrl = `${publicUrl}?width=800`
```

## Troubleshooting

### "Bucket not found" error
Make sure you've created the bucket with the exact ID `lecture-images`

### "Permission denied" error
Check that:
1. The bucket is set to public
2. RLS policies are correctly set up
3. User is authenticated when uploading

### Images not displaying
Verify that:
1. The public URL is correctly formatted
2. The bucket is public
3. CORS is properly configured (should be automatic for public buckets)

## Migration from File Storage

If migrating existing images:

1. Export current image metadata
2. Upload files to Supabase Storage
3. Update database records with new URLs
4. Update application code to use new URLs