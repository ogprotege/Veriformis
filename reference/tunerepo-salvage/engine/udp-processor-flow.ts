'use server';
/**
 * @fileOverview UDP (Universal Document Processor) flow for document ingestion, cleaning, and transformation.
 *
 * - runUDPProcessor - Processes documents with cleaning, chunking, and formatting
 * - UDPInput - The input type for the flow
 * - UDPOutput - The return type for the flow
 */

import { ai } from '@/ai/genkit';
import { z } from 'genkit';

// Schema for UDP input
const UDPInputSchema = z.object({
  content: z.string().describe('The document content to process'),
  contentType: z.enum(['text', 'markdown', 'html', 'pdf', 'docx']).describe('Type of content being processed'),
  cleaningOptions: z.object({
    removeHeaders: z.boolean().default(false).describe('Remove headers and footers'),
    removePageNumbers: z.boolean().default(true).describe('Remove page numbers'),
    removeExtraWhitespace: z.boolean().default(true).describe('Normalize whitespace'),
    removeSpecialChars: z.boolean().default(false).describe('Remove special characters'),
    convertToLowercase: z.boolean().default(false).describe('Convert text to lowercase'),
    removeUrls: z.boolean().default(false).describe('Remove URLs from text'),
    removeEmails: z.boolean().default(false).describe('Remove email addresses'),
    customRegexPatterns: z.array(z.string()).optional().describe('Custom regex patterns to remove'),
  }).describe('Document cleaning options'),
  chunkingStrategy: z.object({
    method: z.enum(['fixed', 'semantic', 'paragraph', 'sentence', 'sliding']).describe('Chunking method'),
    chunkSize: z.number().min(100).max(10000).default(1000).describe('Target chunk size in characters'),
    overlap: z.number().min(0).max(500).default(100).describe('Overlap between chunks'),
    preserveContext: z.boolean().default(true).describe('Try to preserve semantic context'),
  }).describe('Document chunking strategy'),
  outputFormat: z.enum(['jsonl', 'csv', 'text', 'markdown']).describe('Desired output format'),
  enhancementOptions: z.object({
    addMetadata: z.boolean().default(true).describe('Add metadata to chunks'),
    generateSummaries: z.boolean().default(false).describe('Generate summaries for chunks'),
    extractKeywords: z.boolean().default(false).describe('Extract keywords from chunks'),
    detectLanguage: z.boolean().default(true).describe('Detect language of content'),
  }).optional().describe('Enhancement options'),
});

export type UDPInput = z.infer<typeof UDPInputSchema>;

// Output schema
const UDPOutputSchema = z.object({
  success: z.boolean(),
  processedChunks: z.array(z.object({
    id: z.string(),
    content: z.string(),
    metadata: z.object({
      chunkIndex: z.number(),
      startChar: z.number(),
      endChar: z.number(),
      wordCount: z.number(),
      language: z.string().optional(),
      summary: z.string().optional(),
      keywords: z.array(z.string()).optional(),
    }),
  })),
  statistics: z.object({
    originalLength: z.number(),
    processedLength: z.number(),
    chunkCount: z.number(),
    averageChunkSize: z.number(),
    removedCharacters: z.number(),
    processingTime: z.number(),
  }),
  outputData: z.string().describe('Formatted output based on selected format'),
  warnings: z.array(z.string()).optional(),
});

export type UDPOutput = z.infer<typeof UDPOutputSchema>;

// Helper function to clean text
function cleanText(text: string, options: UDPInput['cleaningOptions']): string {
  let cleaned = text;

  if (options.removeExtraWhitespace) {
    cleaned = cleaned.replace(/\s+/g, ' ').trim();
  }

  if (options.removePageNumbers) {
    // Remove common page number patterns
    cleaned = cleaned.replace(/\b\d+\s*(?:of\s*\d+)?\b/gi, '');
    cleaned = cleaned.replace(/(?:page|p\.?)\s*\d+/gi, '');
  }

  if (options.removeHeaders) {
    // Remove lines that look like headers (all caps, short lines at start)
    cleaned = cleaned.split('\n').filter(line => {
      const trimmed = line.trim();
      return !(trimmed.length < 50 && trimmed === trimmed.toUpperCase() && trimmed.length > 0);
    }).join('\n');
  }

  if (options.removeUrls) {
    cleaned = cleaned.replace(/https?:\/\/[^\s]+/g, '');
  }

  if (options.removeEmails) {
    cleaned = cleaned.replace(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g, '');
  }

  if (options.removeSpecialChars) {
    cleaned = cleaned.replace(/[^\w\s.,!?-]/g, '');
  }

  if (options.convertToLowercase) {
    cleaned = cleaned.toLowerCase();
  }

  // Apply custom regex patterns
  if (options.customRegexPatterns) {
    options.customRegexPatterns.forEach(pattern => {
      try {
        const regex = new RegExp(pattern, 'g');
        cleaned = cleaned.replace(regex, '');
      } catch {
        // Invalid regex, skip
      }
    });
  }

  return cleaned;
}

// Helper function to chunk text
function chunkText(text: string, strategy: UDPInput['chunkingStrategy']): string[] {
  const chunks: string[] = [];
  
  switch (strategy.method) {
    case 'fixed':
      // Fixed size chunks with overlap
      for (let i = 0; i < text.length; i += strategy.chunkSize - strategy.overlap) {
        chunks.push(text.slice(i, i + strategy.chunkSize));
      }
      break;
      
    case 'sentence':
      // Split by sentences
      const sentences = text.match(/[^.!?]+[.!?]+/g) || [text];
      let currentChunk = '';
      
      sentences.forEach(sentence => {
        if (currentChunk.length + sentence.length <= strategy.chunkSize) {
          currentChunk += sentence + ' ';
        } else {
          if (currentChunk) chunks.push(currentChunk.trim());
          currentChunk = sentence + ' ';
        }
      });
      if (currentChunk) chunks.push(currentChunk.trim());
      break;
      
    case 'paragraph':
      // Split by paragraphs
      const paragraphs = text.split(/\n\n+/);
      paragraphs.forEach(para => {
        if (para.length <= strategy.chunkSize) {
          chunks.push(para);
        } else {
          // If paragraph is too long, use fixed chunking
          for (let i = 0; i < para.length; i += strategy.chunkSize - strategy.overlap) {
            chunks.push(para.slice(i, i + strategy.chunkSize));
          }
        }
      });
      break;
      
    case 'sliding':
      // Sliding window with overlap
      const step = Math.max(1, strategy.chunkSize - strategy.overlap);
      for (let i = 0; i < text.length - strategy.chunkSize + 1; i += step) {
        chunks.push(text.slice(i, i + strategy.chunkSize));
      }
      break;
      
    case 'semantic':
      // Simplified semantic chunking - split on paragraph boundaries but respect size limits
      const semanticParagraphs = text.split(/\n+/);
      let semanticChunk = '';
      
      semanticParagraphs.forEach(para => {
        if (semanticChunk.length + para.length <= strategy.chunkSize) {
          semanticChunk += para + '\n\n';
        } else {
          if (semanticChunk) chunks.push(semanticChunk.trim());
          semanticChunk = para + '\n\n';
        }
      });
      if (semanticChunk) chunks.push(semanticChunk.trim());
      break;
  }
  
  return chunks.filter(chunk => chunk.length > 0);
}

// Format output based on selected format
function formatOutput(chunks: UDPOutput['processedChunks'], format: UDPInput['outputFormat']): string {
  switch (format) {
    case 'jsonl':
      return chunks.map(chunk => JSON.stringify(chunk)).join('\n');
      
    case 'csv':
      const headers = ['id', 'content', 'chunk_index', 'word_count', 'language'];
      const rows = chunks.map(chunk => [
        chunk.id,
        `"${chunk.content.replace(/"/g, '""')}"`,
        chunk.metadata.chunkIndex,
        chunk.metadata.wordCount,
        chunk.metadata.language || 'unknown'
      ]);
      return [headers.join(','), ...rows.map(row => row.join(','))].join('\n');
      
    case 'text':
      return chunks.map(chunk => chunk.content).join('\n\n---\n\n');
      
    case 'markdown':
      return chunks.map(chunk => 
        `## Chunk ${chunk.metadata.chunkIndex + 1}\n\n${chunk.content}\n\n` +
        `*Words: ${chunk.metadata.wordCount}*\n`
      ).join('\n---\n\n');
      
    default:
      return JSON.stringify(chunks, null, 2);
  }
}

export const runUDPProcessor = ai.defineFlow(
  {
    name: 'udpProcessor',
    inputSchema: UDPInputSchema,
    outputSchema: UDPOutputSchema,
  },
  async (input) => {
    const startTime = Date.now();
    const warnings: string[] = [];
    
    try {
      // Step 1: Clean the document
      const originalLength = input.content.length;
      const cleanedContent = cleanText(input.content, input.cleaningOptions);
      const processedLength = cleanedContent.length;
      
      if (processedLength < originalLength * 0.5) {
        warnings.push('More than 50% of content was removed during cleaning. Consider adjusting cleaning options.');
      }
      
      // Step 2: Chunk the document
      const rawChunks = chunkText(cleanedContent, input.chunkingStrategy);
      
      if (rawChunks.length === 0) {
        throw new Error('No chunks generated from the document. The content may be too short or cleaning too aggressive.');
      }
      
      // Step 3: Process chunks and add metadata
      const processedChunks: UDPOutput['processedChunks'] = [];
      let currentPosition = 0;
      
      for (let i = 0; i < rawChunks.length; i++) {
        const chunk = rawChunks[i];
        const chunkData: UDPOutput['processedChunks'][0] = {
          id: `chunk_${i + 1}_${Date.now()}`,
          content: chunk,
          metadata: {
            chunkIndex: i,
            startChar: currentPosition,
            endChar: currentPosition + chunk.length,
            wordCount: chunk.split(/\s+/).filter(word => word.length > 0).length,
          },
        };
        
        // Add enhancements if requested
        if (input.enhancementOptions) {
          if (input.enhancementOptions.detectLanguage) {
            // Simple language detection (in real implementation, use a proper library)
            const commonEnglishWords = ['the', 'is', 'at', 'which', 'on', 'and', 'a', 'to'];
            const words = chunk.toLowerCase().split(/\s+/);
            const englishWordCount = words.filter(w => commonEnglishWords.includes(w)).length;
            chunkData.metadata.language = englishWordCount > words.length * 0.05 ? 'en' : 'unknown';
          }
          
          if (input.enhancementOptions.extractKeywords) {
            // Simple keyword extraction (frequency-based)
            const words = chunk.toLowerCase().split(/\s+/)
              .filter(w => w.length > 4 && !['which', 'where', 'there', 'these', 'those', 'about'].includes(w));
            const wordFreq = words.reduce((acc, word) => {
              acc[word] = (acc[word] || 0) + 1;
              return acc;
            }, {} as Record<string, number>);
            
            chunkData.metadata.keywords = Object.entries(wordFreq)
              .sort((a, b) => b[1] - a[1])
              .slice(0, 5)
              .map(([word]) => word);
          }
          
          if (input.enhancementOptions.generateSummaries && ai.generate) {
            try {
              // Use AI to generate summary
              const summaryResult = await ai.generate({
                model: 'googleai/gemini-1.5-flash-latest',
                prompt: `Summarize this text in one sentence (max 20 words):\n\n${chunk.slice(0, 500)}`,
                config: { maxOutputTokens: 50 }
              });
              chunkData.metadata.summary = summaryResult.text.trim();
            } catch {
              // Fallback to first sentence
              chunkData.metadata.summary = chunk.split(/[.!?]/)[0].slice(0, 100) + '...';
            }
          }
        }
        
        processedChunks.push(chunkData);
        currentPosition += chunk.length;
      }
      
      // Step 4: Calculate statistics
      const statistics: UDPOutput['statistics'] = {
        originalLength,
        processedLength,
        chunkCount: processedChunks.length,
        averageChunkSize: Math.round(processedLength / processedChunks.length),
        removedCharacters: originalLength - processedLength,
        processingTime: Date.now() - startTime,
      };
      
      // Step 5: Format output
      const outputData = formatOutput(processedChunks, input.outputFormat);
      
      return {
        success: true,
        processedChunks,
        statistics,
        outputData,
        warnings: warnings.length > 0 ? warnings : undefined,
      };
      
    } catch (error) {
      throw new Error(`UDP processing failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }
);