'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Plus, Trash2, Mail, Globe } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';
import { apiRequest } from '@/lib/api';

interface EmailWhitelistEntry {
  id: string;
  email_pattern: string;
  is_domain: boolean;
  created_at: string;
}

export default function EmailWhitelistPage() {
  const { toast } = useToast();
  const [entries, setEntries] = useState<EmailWhitelistEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [newEntry, setNewEntry] = useState({
    email_pattern: '',
    is_domain: false
  });

  useEffect(() => {
    loadWhitelist();
  }, []);

  const loadWhitelist = async () => {
    try {
      const data = await apiRequest('/v1/admin/whitelist');
      setEntries(data);
    } catch (err) {
      toast({
        title: 'Error',
        description: 'Failed to load email whitelist',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const addToWhitelist = async () => {
    try {
      await apiRequest('/v1/admin/whitelist', {
        method: 'POST',
        body: JSON.stringify(newEntry),
      });
      
      toast({
        title: 'Success',
        description: 'Email pattern added to whitelist',
      });
      
      setShowAddDialog(false);
      setNewEntry({ email_pattern: '', is_domain: false });
      loadWhitelist();
    } catch (err) {
      toast({
        title: 'Error',
        description: 'Failed to add email pattern',
        variant: 'destructive',
      });
    }
  };

  const removeFromWhitelist = async (id: string) => {
    try {
      await apiRequest(`/v1/admin/whitelist/${id}`, {
        method: 'DELETE',
      });
      
      toast({
        title: 'Success',
        description: 'Email pattern removed from whitelist',
      });
      
      loadWhitelist();
    } catch (err) {
      toast({
        title: 'Error',
        description: 'Failed to remove email pattern',
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Email Whitelist</h1>
        <p className="text-gray-600">Manage which emails and domains can register and login</p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <CardTitle>Whitelisted Emails & Domains</CardTitle>
            <Button onClick={() => setShowAddDialog(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add Entry
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>Pattern</TableHead>
                  <TableHead>Added</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {entries.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center py-8 text-gray-500">
                      No whitelist entries found
                    </TableCell>
                  </TableRow>
                ) : (
                  entries.map((entry) => (
                    <TableRow key={entry.id}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {entry.is_domain ? (
                            <>
                              <Globe className="h-4 w-4 text-blue-500" />
                              <span className="text-sm">Domain</span>
                            </>
                          ) : (
                            <>
                              <Mail className="h-4 w-4 text-green-500" />
                              <span className="text-sm">Email</span>
                            </>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="font-mono">
                        {entry.is_domain ? `@${entry.email_pattern}` : entry.email_pattern}
                      </TableCell>
                      <TableCell className="text-sm text-gray-500">
                        {new Date(entry.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-red-600 hover:text-red-700"
                          onClick={() => removeFromWhitelist(entry.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Add Entry Dialog */}
      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add to Email Whitelist</DialogTitle>
            <DialogDescription>
              Add an email address or domain to allow registration and login
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div className="flex items-center space-x-2">
              <Checkbox
                id="is-domain"
                checked={newEntry.is_domain}
                onCheckedChange={(checked) => 
                  setNewEntry({ ...newEntry, is_domain: checked as boolean })
                }
              />
              <Label htmlFor="is-domain">
                This is a domain (e.g., university.edu)
              </Label>
            </div>
            
            <div>
              <Label>
                {newEntry.is_domain ? 'Domain' : 'Email Address'}
              </Label>
              <Input
                placeholder={newEntry.is_domain ? 'university.edu' : 'admin@university.edu'}
                value={newEntry.email_pattern}
                onChange={(e) => 
                  setNewEntry({ ...newEntry, email_pattern: e.target.value })
                }
              />
              {newEntry.is_domain && (
                <p className="text-xs text-gray-500 mt-1">
                  Don't include the @ symbol for domains
                </p>
              )}
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddDialog(false)}>
              Cancel
            </Button>
            <Button 
              onClick={addToWhitelist}
              disabled={!newEntry.email_pattern.trim()}
            >
              Add to Whitelist
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}