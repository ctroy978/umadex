'use client';

import { useEffect, useState } from 'react';
import { AuditLogEntry } from '@/types/admin';
import { adminApi } from '@/lib/adminApi';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Search } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

export default function AdminAuditLogPage() {
  const [auditLog, setAuditLog] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [actionTypeFilter, setActionTypeFilter] = useState<string>('all');
  const [currentPage, setCurrentPage] = useState(1);

  useEffect(() => {
    loadAuditLog();
  }, [currentPage, actionTypeFilter]);

  const loadAuditLog = async () => {
    try {
      setLoading(true);
      const data = await adminApi.getAuditLog({
        page: currentPage,
        per_page: 50,
        action_type: actionTypeFilter === 'all' ? undefined : actionTypeFilter,
      });
      // Extract the actions array from the response
      setAuditLog(data.actions || []);
    } catch (err) {
      console.error('Failed to load audit log:', err);
      setAuditLog([]); // Set empty array on error
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Audit Log</h1>
        <p className="text-gray-600">View all administrative actions</p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <Input
                placeholder="Search actions..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>
          <Select value={actionTypeFilter} onValueChange={setActionTypeFilter}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Filter by action type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Actions</SelectItem>
              <SelectItem value="user_promotion">User Promotions</SelectItem>
              <SelectItem value="user_soft_delete">Soft Deletes</SelectItem>
              <SelectItem value="user_hard_delete">Hard Deletes</SelectItem>
              <SelectItem value="user_restore">User Restores</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Audit Log */}
      <Card>
        <CardHeader>
          <CardTitle>Administrative Actions</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
            </div>
          ) : auditLog.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No audit log entries found
            </div>
          ) : (
            <div className="space-y-4">
              {auditLog.map((entry) => (
                <div key={entry.id} className="border rounded-lg p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="font-medium text-gray-900">
                          {entry.action_type.replace('_', ' ').toUpperCase()}
                        </span>
                        <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                          {entry.admin_email}
                        </span>
                      </div>
                      {entry.action_data && Object.keys(entry.action_data).length > 0 && (
                        <div className="text-sm text-gray-600 mb-2">
                          <pre className="bg-gray-50 p-2 rounded text-xs overflow-x-auto">
                            {JSON.stringify(entry.action_data, null, 2)}
                          </pre>
                        </div>
                      )}
                      {entry.target_id && (
                        <div className="text-sm text-gray-500">
                          Target: {entry.target_type} {entry.target_id}
                        </div>
                      )}
                    </div>
                    <div className="text-right text-sm text-gray-500">
                      {formatDistanceToNow(new Date(entry.created_at), { addSuffix: true })}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}