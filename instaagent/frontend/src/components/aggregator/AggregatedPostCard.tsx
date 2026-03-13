"use client";
import React from 'react';
import { Card, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Heart, MessageCircle, Save, EyeOff, Trash2 } from 'lucide-react';

export default function AggregatedPostCard({ post, onSave, onHide, onDelete, isAdmin = false }) {
  return (
    <Card className="overflow-hidden group">
      <div className="aspect-square bg-muted relative overflow-hidden">
        <img 
          src={post.media_url || "/api/placeholder/400/400"} 
          alt={post.caption} 
          className="object-cover w-full h-full transition-transform duration-500 group-hover:scale-105"
        />
        {post.hidden && (
          <div className="absolute inset-0 bg-black/60 flex items-center justify-center text-white text-sm font-medium">
            Hidden from Feed
          </div>
        )}
      </div>
      <CardContent className="p-4">
        <p className="text-sm line-clamp-2 mb-3">{post.caption}</p>
        <div className="flex gap-4 text-xs font-semibold text-muted-foreground">
          <span className="flex items-center gap-1"><Heart className="w-3 h-3" /> {post.likes}</span>
          <span className="flex items-center gap-1"><MessageCircle className="w-3 h-3" /> {post.comments}</span>
        </div>
      </CardContent>
      <CardFooter className="p-4 pt-0 flex flex-wrap gap-2">
        <Button size="sm" variant="secondary" className="flex-1 gap-2" onClick={() => onSave(post.id)}>
          <Save className="w-3 h-3" /> Save to My Posts
        </Button>
        {isAdmin && (
          <>
            <Button size="sm" variant="outline" className="px-3" onClick={() => onHide(post.id)}>
              <EyeOff className="w-4 h-4" />
            </Button>
            <Button size="sm" variant="destructive" className="px-3" onClick={() => onDelete(post.id)}>
              <Trash2 className="w-4 h-4" />
            </Button>
          </>
        )}
      </CardFooter>
    </Card>
  );
}
