"use client";
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { RefreshCw, TrendingUp, Users, FileText } from 'lucide-react';
import { toast } from 'react-hot-toast';
import AggregatedPostCard from '@/components/aggregator/AggregatedPostCard';

import { api } from "../../../components/common/api";

export default function AdminAggregatorPage() {
  const [stats, setStats] = useState(null);
  const [trends, setTrends] = useState([]);
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('ia_token') || localStorage.getItem('token');
      const [s, t, p] = await Promise.all([
        api.get('/api/v1/aggregator/admin/stats', token),
        api.get('/api/v1/aggregator/admin/trends', token),
        api.get('/api/v1/aggregator/posts?limit=20', token)
      ]);
      setStats(s);
      setTrends(t.trends || []);
      setPosts(p);
    } catch (err) {
      toast.error("Admin access denied or server error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const handleModerate = async (postId, hidden) => {
    try {
      const token = localStorage.getItem('ia_token') || localStorage.getItem('token');
      await api.patch(`/api/v1/aggregator/admin/posts/${postId}`, { hidden }, token);
      toast.success("Post visibility updated");
      fetchData();
    } catch (err) {
      toast.error("Moderation failed");
    }
  };

  const handleDelete = async (postId) => {
    if (!confirm("Delete post permanently?")) return;
    try {
      const token = localStorage.getItem('ia_token') || localStorage.getItem('token');
      await api.del(`/api/v1/aggregator/admin/posts/${postId}`, token);
      toast.success("Post deleted");
      fetchData();
    } catch (err) {
      toast.error("Delete failed");
    }
  };

  if (loading && !stats) return <div className="p-20 text-center">Loading admin insights...</div>;

  return (
    <div className="container mx-auto p-6 space-y-8">
      <h1 className="text-3xl font-bold">Aggregator Overview (Admin)</h1>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="bg-primary/5">
          <CardHeader className="p-4"><CardTitle className="text-xs uppercase text-muted-foreground flex items-center gap-2"><Users className="w-4 h-4" /> Users</CardTitle></CardHeader>
          <CardContent className="px-4 pb-4"><div className="text-2xl font-bold">{stats?.active_users}</div></CardContent>
        </Card>
        <Card className="bg-accent/5">
          <CardHeader className="p-4"><CardTitle className="text-xs uppercase text-muted-foreground flex items-center gap-2"><RefreshCw className="w-4 h-4" /> Tracked Accounts</CardTitle></CardHeader>
          <CardContent className="px-4 pb-4"><div className="text-2xl font-bold">{stats?.total_tracked_accounts}</div></CardContent>
        </Card>
        <Card className="bg-secondary/5">
          <CardHeader className="p-4"><CardTitle className="text-xs uppercase text-muted-foreground flex items-center gap-2"><FileText className="w-4 h-4" /> Total Posts</CardTitle></CardHeader>
          <CardContent className="px-4 pb-4"><div className="text-2xl font-bold">{stats?.total_aggregated_posts}</div></CardContent>
        </Card>
        <Card className="bg-yellow-500/5">
          <CardHeader className="p-4"><CardTitle className="text-xs uppercase text-muted-foreground flex items-center gap-2"><TrendingUp className="w-4 h-4" /> Trending Tags</CardTitle></CardHeader>
          <CardContent className="px-4 pb-4"><div className="text-2xl font-bold">{trends.length} Identified</div></CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <Card>
          <CardHeader><CardTitle>User Activity Breakdown</CardTitle></CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>User</TableHead>
                  <TableHead className="text-right">Accounts</TableHead>
                  <TableHead className="text-right">Posts</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {stats?.user_details?.map(u => (
                  <TableRow key={u.id}>
                    <TableCell><div className="font-medium">{u.full_name}</div><div className="text-xs text-muted-foreground">{u.email}</div></TableCell>
                    <TableCell className="text-right font-bold">{u.account_count}</TableCell>
                    <TableCell className="text-right text-primary font-bold">{u.post_count}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Trending Across Platform</CardTitle></CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {trends.map(t => (
                <Badge key={t.tag} variant="outline" className="text-lg py-2 px-4 gap-2">
                  <span className="text-primary">#{t.tag}</span>
                  <span className="text-muted-foreground font-normal">{t.count}</span>
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="space-y-4">
        <h2 className="text-2xl font-bold">Global Content Moderation</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {posts.map(p => (
            <AggregatedPostCard 
              key={p.id} 
              post={p} 
              isAdmin={true} 
              onHide={() => handleModerate(p.id, !p.hidden)}
              onDelete={() => handleDelete(p.id)}
              onSave={() => {}}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
