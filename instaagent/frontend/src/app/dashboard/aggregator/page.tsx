"use client";
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { PlusCircle, Sparkles, LayoutGrid, List } from 'lucide-react';
import AggregatorAccountCard from '@/components/aggregator/AggregatorAccountCard';
import AggregatedPostCard from '@/components/aggregator/AggregatedPostCard';
import AIInsightsPanel from '@/components/aggregator/AIInsightsPanel';
import { toast } from 'react-hot-toast';

export default function AggregatorPage() {
  const [accounts, setAccounts] = useState([]);
  const [posts, setPosts] = useState([]);
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newAccount, setNewAccount] = useState({ username: '', type: 'competitor' });

  const token = localStorage.getItem('token');
  const api = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    headers: { Authorization: `Bearer ${token}` }
  });

  const fetchData = async () => {
    setLoading(true);
    try {
      const [accs, pts] = await Promise.all([
        api.get('/api/v1/aggregator/accounts'),
        api.get('/api/v1/aggregator/posts')
      ]);
      setAccounts(accs.data);
      setPosts(pts.data);
    } catch (err) {
      toast.error("Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const handleAddAccount = async (e) => {
    e.preventDefault();
    try {
      await api.post('/api/v1/aggregator/accounts', {
        instagram_username: newAccount.username,
        account_type: newAccount.type
      });
      toast.success("Account added! Sync started.");
      setShowAddForm(false);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to add account");
    }
  };

  const handleAnalyze = async () => {
    setLoading(true);
    try {
      const resp = await api.post('/api/v1/aggregator/ai-analyze', {
        account_ids: accounts.map(a => a.id)
      });
      setInsights(resp.data);
      toast.success("Insights generated!");
    } catch (err) {
      toast.error("AI Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-8 animate-in fade-in duration-500">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight">Inspiration Aggregator</h1>
          <p className="text-muted-foreground">Track competitors and generate AI strategy.</p>
        </div>
        <Button onClick={() => setShowAddForm(!showAddForm)} className="gap-2">
          <PlusCircle className="w-4 h-4" /> Add Account
        </Button>
      </div>

      {showAddForm && (
        <Card className="max-w-md animate-in slide-in-from-top-4 duration-300">
          <CardHeader><CardTitle className="text-lg">Add New Account</CardTitle></CardHeader>
          <CardContent>
            <form onSubmit={handleAddAccount} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="username">Instagram Username</Label>
                <Input 
                  id="username" 
                  placeholder="e.g. zuck" 
                  value={newAccount.username}
                  onChange={(e) => setNewAccount({...newAccount, username: e.target.value})}
                  required 
                />
              </div>
              <div className="space-y-2">
                <Label>Account Type</Label>
                <Select value={newAccount.type} onValueChange={(v) => setNewAccount({...newAccount, type: v})}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="owned">My Account</SelectItem>
                    <SelectItem value="competitor">Competitor / Public</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Button type="submit" className="w-full">Start Tracking</Button>
            </form>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {accounts.map(acc => (
          <AggregatorAccountCard 
            key={acc.id} 
            account={acc} 
            onRefresh={() => api.post(`/api/v1/aggregator/refresh/${acc.id}`)}
          />
        ))}
      </div>

      <div className="flex gap-4 items-center pt-8 border-t">
        <h2 className="text-2xl font-bold flex-1">Inspiration Feed</h2>
        <Button variant="outline" onClick={handleAnalyze} disabled={loading || posts.length === 0} className="gap-2">
          <Sparkles className="w-4 h-4" /> Generate AI Strategy
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-6">
          {posts.map(post => (
            <AggregatedPostCard 
              key={post.id} 
              post={post} 
              onSave={() => api.post(`/api/v1/aggregator/posts/${post.id}/save`)}
            />
          ))}
          {posts.length === 0 && (
            <div className="col-span-full py-20 text-center border-2 border-dashed rounded-3xl">
              <p className="text-muted-foreground">No posts yet. Add accounts to start aggregating.</p>
            </div>
          )}
        </div>
        <div className="space-y-6">
          <AIInsightsPanel insights={insights} />
        </div>
      </div>
    </div>
  );
}
