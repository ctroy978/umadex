'use client';

import React, { useMemo } from 'react';

interface ChunkPreviewProps {
  content: string;
}

interface ParsedChunk {
  content: string;
  hasImportant: boolean;
  order: number;
}

export default function ChunkPreview({ content }: ChunkPreviewProps) {
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
    // Replace important tags with styled spans
    let processedContent = chunkContent
      .replace(/<important>/g, '<span class="bg-yellow-200 font-semibold px-1">')
      .replace(/<\/important>/g, '</span>')
      .replace(/<image>(.*?)<\/image>/g, '<span class="inline-block bg-blue-100 text-blue-700 px-2 py-1 rounded text-sm">📷 $1</span>');
    
    return (
      <div 
        className="text-sm text-gray-700 leading-relaxed"
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
              className="border border-gray-200 rounded-lg p-3 hover:border-blue-300 transition-colors"
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
              
              <div className="prose prose-sm max-w-none">
                {renderChunkContent(chunk.content)}
              </div>
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