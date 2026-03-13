"use client";
import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Lightbulb, TrendingUp, Clock, Type } from 'lucide-react';

export default function AIInsightsPanel({ insights }) {
  if (!insights) return null;

  return (
    <Card className="bg-gradient-to-br from-primary/5 to-accent/5 border-primary/20">
      <CardHeader>
        <CardTitle className="text-xl flex items-center gap-2">
          <Lightbulb className="w-5 h-5 text-primary" /> AI-Generated Strategy
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="ideas" className="w-full">
          <TabsList className="grid grid-cols-4 mb-6">
            <TabsTrigger value="ideas" className="gap-2"><Type className="w-4 h-4" /> Ideas</TabsTrigger>
            <TabsTrigger value="trends" className="gap-2"><TrendingUp className="w-4 h-4" /> Trends</TabsTrigger>
            <TabsTrigger value="times" className="gap-2"><Clock className="w-4 h-4" /> Times</TabsTrigger>
            <TabsTrigger value="captions" className="gap-2">Captions</TabsTrigger>
          </TabsList>
          
          <TabsContent value="ideas" className="space-y-4">
            {insights.post_ideas?.map((idea, i) => (
              <div key={i} className="p-3 bg-background/50 border rounded-lg text-sm">{idea}</div>
            ))}
          </TabsContent>
          <TabsContent value="trends" className="space-y-4">
            {insights.trend_summaries?.map((trend, i) => (
              <div key={i} className="p-3 bg-background/50 border rounded-lg text-sm italic font-medium">#{trend}</div>
            ))}
          </TabsContent>
          <TabsContent value="times" className="grid grid-cols-2 gap-3">
            {insights.best_posting_times?.map((time, i) => (
              <div key={i} className="p-3 bg-primary/10 border border-primary/20 rounded-lg text-center font-bold text-primary">{time}</div>
            ))}
          </TabsContent>
          <TabsContent value="captions" className="space-y-4">
            {insights.caption_suggestions?.map((caption, i) => (
              <div key={i} className="p-3 bg-secondary/10 border rounded-lg text-sm">{caption}</div>
            ))}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
