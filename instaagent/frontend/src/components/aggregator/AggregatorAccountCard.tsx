"use client";
import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { RefreshCw, Trash2, Shield } from 'lucide-react';

export default function AggregatorAccountCard({ account, onRefresh, onDelete, isAdmin = false }) {
  return (
    <Card className="hover:shadow-md transition-shadow duration-200">
      <CardHeader className="pb-2">
        <div className="flex justify-between items-start">
          <div className="flex flex-col">
            <CardTitle className="text-lg font-bold flex items-center gap-2">
              @{account.instagram_username}
              {account.account_type === 'owned' && <Shield className="w-4 h-4 text-primary" />}
            </CardTitle>
            <span className="text-xs text-muted-foreground uppercase tracking-wider">{account.account_type}</span>
          </div>
          <Badge variant={account.sync_error ? "destructive" : "secondary"}>
             {account.sync_error ? "Failed" : account.last_synced_at ? "Synced" : "Pending"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col gap-4">
          <div className="text-sm text-muted-foreground">
            Last synced: {account.last_synced_at ? new Date(account.last_synced_at).toLocaleString() : 'Never'}
          </div>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" className="w-full gap-2" onClick={() => onRefresh(account.id)}>
              <RefreshCw className="w-3 h-3" /> Refresh
            </Button>
            {isAdmin && (
              <Button size="sm" variant="destructive" className="px-3" onClick={() => onDelete(account.id)}>
                <Trash2 className="w-4 h-4" />
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
