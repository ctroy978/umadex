-- Create storage buckets for images

-- Create bucket for reading assignment images
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES 
  ('reading-images', 'reading-images', true, 5242880, ARRAY['image/jpeg', 'image/png', 'image/gif', 'image/webp'])
ON CONFLICT (id) DO UPDATE SET
  public = true,
  file_size_limit = 5242880,
  allowed_mime_types = ARRAY['image/jpeg', 'image/png', 'image/gif', 'image/webp'];

-- Create bucket for lecture images (if not exists)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES 
  ('lecture-images', 'lecture-images', true, 5242880, ARRAY['image/jpeg', 'image/png', 'image/gif', 'image/webp'])
ON CONFLICT (id) DO UPDATE SET
  public = true,
  file_size_limit = 5242880,
  allowed_mime_types = ARRAY['image/jpeg', 'image/png', 'image/gif', 'image/webp'];

-- Create RLS policies for reading-images bucket
CREATE POLICY "Allow authenticated uploads to reading-images" 
ON storage.objects 
FOR INSERT 
TO authenticated 
WITH CHECK (bucket_id = 'reading-images');

CREATE POLICY "Allow authenticated updates to reading-images" 
ON storage.objects 
FOR UPDATE 
TO authenticated 
USING (bucket_id = 'reading-images');

CREATE POLICY "Allow authenticated deletes from reading-images" 
ON storage.objects 
FOR DELETE 
TO authenticated 
USING (bucket_id = 'reading-images');

CREATE POLICY "Allow public reads from reading-images" 
ON storage.objects 
FOR SELECT 
TO public 
USING (bucket_id = 'reading-images');

-- Create RLS policies for lecture-images bucket
CREATE POLICY "Allow authenticated uploads to lecture-images" 
ON storage.objects 
FOR INSERT 
TO authenticated 
WITH CHECK (bucket_id = 'lecture-images');

CREATE POLICY "Allow authenticated updates to lecture-images" 
ON storage.objects 
FOR UPDATE 
TO authenticated 
USING (bucket_id = 'lecture-images');

CREATE POLICY "Allow authenticated deletes from lecture-images" 
ON storage.objects 
FOR DELETE 
TO authenticated 
USING (bucket_id = 'lecture-images');

CREATE POLICY "Allow public reads from lecture-images" 
ON storage.objects 
FOR SELECT 
TO public 
USING (bucket_id = 'lecture-images');