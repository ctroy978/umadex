'use client';

import React, { useMemo } from 'react';

import { AssignmentImage } from '@/types/reading';

interface ChunkPreviewProps {
  content: string;
  images?: AssignmentImage[];
}

interface ParsedChunk {
  content: string;
  hasImportant: boolean;
  order: number;
}

export default function ChunkPreview({ content, images = [] }: ChunkPreviewProps) {
  const chunks = useMemo(() => {
    const chunkRegex = /<chunk>([\s\S]*?)<\/chunk>/g;
    const parsedChunks: ParsedChunk[] = [];
    let match;
    let order = 1;

    while ((match = chunkRegex.exec(content)) !== null) {
      const chunkContent = match[1].trim();
      const hasImportant = chunkContent.includes('<important>');
      
      parsedChunks.push({
        content: chunkContent,
        hasImportant,
        order: order++,
      });
    }

    return parsedChunks;
  }, [content]);

  const renderChunkContent = (chunkContent: string) => {
    // First, preserve line breaks by converting them to <br> tags
    let processedContent = chunkContent
      .split('\n\n')
      .map(paragraph => `<p>${paragraph.trim()}</p>`)
      .join('')
      .replace(/\n/g, '<br />');
    
    // Replace important tags with styled spans
    processedContent = processedContent
      .replace(/<important>/g, '<span class="bg-yellow-200 font-semibold px-1">')
      .replace(/<\/important>/g, '</span>');
    
    // Replace image tags with actual images with floating
    processedContent = processedContent.replace(/<image>(.*?)<\/image>/g, (match, imageTag) => {
      const image = images.find(img => img.image_tag === imageTag.trim());
      if (image && image.display_url) {
        // If the URL is already absolute (starts with http:// or https://), use it directly
        // Otherwise, prepend the API URL for legacy images
        let imageUrl: string;
        if (image.display_url.startsWith('http://') || image.display_url.startsWith('https://')) {
          imageUrl = image.display_url;
        } else {
          // For relative URLs, prepend the base URL (without /api)
          const baseUrl = process.env.NEXT_PUBLIC_API_URL?.replace('/api', '') || 'http://localhost';
          imageUrl = `${baseUrl}${image.display_url}`;
        }
        return `<img src="${imageUrl}" alt="${imageTag}" class="float-right ml-4 mb-2 w-48 h-auto object-cover rounded shadow-md" title="${image.file_name || imageTag}" />`;
      }
      return `<span class="inline-block bg-red-100 text-red-700 px-2 py-1 rounded text-sm">⚠️ ${imageTag} not found</span>`;
    });
    
    return (
      <div 
        className="text-sm text-gray-700 leading-relaxed prose prose-sm max-w-none [&>p]:mb-3 [&>p:last-child]:mb-0"
        dangerouslySetInnerHTML={{ __html: processedContent }}
      />
    );
  };

  return (
    <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
      <h3 className="text-lg font-medium mb-4">Chunk Preview</h3>
      
      {chunks.length === 0 ? (
        <p className="text-sm text-gray-500">
          No chunks found. Use &lt;chunk&gt; tags to divide your content.
        </p>
      ) : (
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {chunks.map((chunk, index) => (
            <div
              key={index}
              className="border border-gray-200 rounded-lg p-3 hover:border-blue-300 transition-colors overflow-hidden"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-gray-500">
                  Chunk {chunk.order}
                </span>
                {chunk.hasImportant && (
                  <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-1 rounded">
                    Has important
                  </span>
                )}
              </div>
              
              {renderChunkContent(chunk.content)}
            </div>
          ))}
        </div>
      )}
      
      <div className="mt-4 pt-4 border-t border-gray-200">
        <p className="text-xs text-gray-500">
          Total chunks: {chunks.length}
        </p>
      </div>
    </div>
  );
}