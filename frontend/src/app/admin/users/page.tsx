'use client';

import { useEffect, useState } from 'react';
import { AdminUser, UserImpactAnalysis } from '@/types/admin';
import { adminApi } from '@/lib/adminApi';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Search, UserPlus, Trash2, RotateCcw, Shield, AlertTriangle, Edit2 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { useToast } from '@/components/ui/use-toast';

export default function AdminUsersPage() {
  const { toast } = useToast();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('all');
  const [includeDeleted, setIncludeDeleted] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  
  // Dialog states
  const [promoteDialog, setPromoteDialog] = useState<{ open: boolean; user?: AdminUser }>({ open: false });
  const [deleteDialog, setDeleteDialog] = useState<{ open: boolean; user?: AdminUser; impact?: UserImpactAnalysis }>({ open: false });
  const [hardDeleteDialog, setHardDeleteDialog] = useState<{ open: boolean; user?: AdminUser }>({ open: false });
  const [editNameDialog, setEditNameDialog] = useState<{ open: boolean; user?: AdminUser }>({ open: false });
  
  // Form states
  const [promotionData, setPromotionData] = useState<{
    new_role?: 'student' | 'teacher';
    make_admin?: boolean;
    reason?: string;
  }>({});
  const [deletionData, setDeletionData] = useState<{
    reason: 'graduation' | 'transfer' | 'disciplinary' | 'inactive' | 'other';
    custom_reason?: string;
    notify_affected_teachers?: boolean;
  }>({ reason: 'other', notify_affected_teachers: false });
  const [confirmationPhrase, setConfirmationPhrase] = useState('');
  const [nameEditData, setNameEditData] = useState<{
    first_name: string;
    last_name: string;
  }>({ first_name: '', last_name: '' });

  useEffect(() => {
    loadUsers();
  }, [currentPage, search, roleFilter, includeDeleted]);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const response = await adminApi.getUsers({
        page: currentPage,
        per_page: 50,
        search: search || undefined,
        role: roleFilter === 'all' ? undefined : roleFilter,
        include_deleted: includeDeleted,
      });
      
      setUsers(response.users);
      setTotal(response.total);
      setTotalPages(response.pages);
    } catch (err) {
      toast({
        title: 'Error',
        description: 'Failed to load users',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handlePromote = async () => {
    if (!promoteDialog.user) return;
    
    try {
      await adminApi.promoteUser(promoteDialog.user.id, promotionData);
      toast({
        title: 'Success',
        description: 'User promoted successfully',
      });
      setPromoteDialog({ open: false });
      setPromotionData({});
      loadUsers();
    } catch (err) {
      toast({
        title: 'Error',
        description: 'Failed to promote user',
        variant: 'destructive',
      });
    }
  };

  const handleSoftDelete = async () => {
    if (!deleteDialog.user) return;
    
    try {
      await adminApi.softDeleteUser(deleteDialog.user.id, deletionData);
      toast({
        title: 'Success',
        description: 'User archived successfully',
      });
      setDeleteDialog({ open: false });
      setDeletionData({ reason: 'other' });
      loadUsers();
    } catch (err) {
      toast({
        title: 'Error',
        description: 'Failed to delete user',
        variant: 'destructive',
      });
    }
  };

  const handleHardDelete = async () => {
    if (!hardDeleteDialog.user) return;
    
    try {
      await adminApi.hardDeleteUser(hardDeleteDialog.user.id, {
        ...deletionData,
        confirmation_phrase: confirmationPhrase,
      });
      toast({
        title: 'Success',
        description: 'User permanently deleted',
      });
      setHardDeleteDialog({ open: false });
      setConfirmationPhrase('');
      loadUsers();
    } catch (err) {
      toast({
        title: 'Error',
        description: 'Failed to delete user',
        variant: 'destructive',
      });
    }
  };

  const handleRestore = async (userId: string) => {
    try {
      await adminApi.restoreUser(userId);
      toast({
        title: 'Success',
        description: 'User restored successfully',
      });
      loadUsers();
    } catch (err) {
      toast({
        title: 'Error',
        description: 'Failed to restore user',
        variant: 'destructive',
      });
    }
  };

  const openDeleteDialog = async (user: AdminUser) => {
    try {
      const impact = await adminApi.getUserImpact(user.id);
      setDeleteDialog({ open: true, user, impact });
    } catch (err) {
      toast({
        title: 'Error',
        description: 'Failed to analyze deletion impact',
        variant: 'destructive',
      });
    }
  };

  const handleUpdateName = async () => {
    console.log('handleUpdateName called');
    console.log('editNameDialog.user:', editNameDialog.user);
    console.log('nameEditData:', nameEditData);
    
    if (!editNameDialog.user) return;
    
    // Client-side validation
    const namePattern = /^[a-zA-Z\s\-']+$/;
    const firstName = nameEditData.first_name.trim();
    const lastName = nameEditData.last_name.trim();
    
    if (!firstName || !lastName) {
      toast({
        title: 'Validation Error',
        description: 'First name and last name are required',
        variant: 'destructive',
      });
      return;
    }
    
    if (firstName.length < 2 || lastName.length < 2) {
      toast({
        title: 'Validation Error',
        description: 'Names must be at least 2 characters long',
        variant: 'destructive',
      });
      return;
    }
    
    if (!namePattern.test(firstName) || !namePattern.test(lastName)) {
      toast({
        title: 'Validation Error',
        description: 'Names can only contain letters, spaces, hyphens, and apostrophes',
        variant: 'destructive',
      });
      return;
    }
    
    try {
      console.log('Calling updateUserName API with:', {
        userId: editNameDialog.user.id,
        data: { first_name: firstName, last_name: lastName }
      });
      
      await adminApi.updateUserName(editNameDialog.user.id, {
        first_name: firstName,
        last_name: lastName
      });
      toast({
        title: 'Success',
        description: 'User name updated successfully',
      });
      setEditNameDialog({ open: false });
      setNameEditData({ first_name: '', last_name: '' });
      loadUsers();
    } catch (err) {
      console.error('Error updating user name:', err);
      toast({
        title: 'Error',
        description: 'Failed to update user name',
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">User Management</h1>
        <p className="text-gray-600">Manage all users in the system</p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <Input
                placeholder="Search by name or email..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>
          <Select value={roleFilter} onValueChange={setRoleFilter}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Filter by role" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Roles</SelectItem>
              <SelectItem value="student">Students</SelectItem>
              <SelectItem value="teacher">Teachers</SelectItem>
              <SelectItem value="admin">Admins</SelectItem>
            </SelectContent>
          </Select>
          <div className="flex items-center space-x-2">
            <Checkbox
              id="include-deleted"
              checked={includeDeleted}
              onCheckedChange={(checked) => setIncludeDeleted(checked as boolean)}
            />
            <Label htmlFor="include-deleted" className="text-sm">
              Show deleted users
            </Label>
          </div>
        </div>
      </div>

      {/* Users Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Joined</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
                </TableCell>
              </TableRow>
            ) : users.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8 text-gray-500">
                  No users found
                </TableCell>
              </TableRow>
            ) : (
              users.map((user) => (
                <TableRow key={user.id} className={user.deleted_at ? 'opacity-50' : ''}>
                  <TableCell className="font-medium">
                    {user.first_name} {user.last_name}
                  </TableCell>
                  <TableCell>{user.email}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <span className={`text-xs px-2 py-1 rounded ${
                        user.role === 'teacher' ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'
                      }`}>
                        {user.role}
                      </span>
                      {user.is_admin && (
                        <Shield className="h-4 w-4 text-purple-500" />
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    {user.deleted_at ? (
                      <span className="text-xs px-2 py-1 rounded bg-red-100 text-red-700">
                        Deleted
                      </span>
                    ) : (
                      <span className="text-xs px-2 py-1 rounded bg-green-100 text-green-700">
                        Active
                      </span>
                    )}
                  </TableCell>
                  <TableCell className="text-sm text-gray-500">
                    {formatDistanceToNow(new Date(user.created_at), { addSuffix: true })}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      {user.deleted_at ? (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleRestore(user.id)}
                        >
                          <RotateCcw className="h-4 w-4" />
                        </Button>
                      ) : (
                        <>
                          <Button
                            size="sm"
                            variant="outline"
                            title="Edit Name"
                            onClick={() => {
                              setEditNameDialog({ open: true, user });
                              setNameEditData({ 
                                first_name: user.first_name, 
                                last_name: user.last_name 
                              });
                            }}
                          >
                            <Edit2 className="h-4 w-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            title="Change Role"
                            onClick={() => {
                              setPromoteDialog({ open: true, user });
                              setPromotionData({ new_role: user.role });
                            }}
                          >
                            <UserPlus className="h-4 w-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            title="Delete User"
                            className="text-red-600 hover:text-red-700"
                            onClick={() => openDeleteDialog(user)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        
        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t">
            <div className="text-sm text-gray-500">
              Showing {(currentPage - 1) * 50 + 1} to {Math.min(currentPage * 50, total)} of {total} users
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => setCurrentPage(currentPage - 1)}
                disabled={currentPage === 1}
              >
                Previous
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setCurrentPage(currentPage + 1)}
                disabled={currentPage === totalPages}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Promote Dialog */}
      <Dialog open={promoteDialog.open} onOpenChange={(open) => setPromoteDialog({ open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Promote User</DialogTitle>
            <DialogDescription>
              Change the role or admin status of {promoteDialog.user?.first_name} {promoteDialog.user?.last_name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>New Role</Label>
              <Select
                value={promotionData.new_role || promoteDialog.user?.role || ''}
                onValueChange={(value) => setPromotionData({ ...promotionData, new_role: value as any })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="student">Student</SelectItem>
                  <SelectItem value="teacher">Teacher</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center space-x-2">
              <Checkbox
                id="make-admin"
                checked={promotionData.make_admin ?? promoteDialog.user?.is_admin ?? false}
                onCheckedChange={(checked) => setPromotionData({ ...promotionData, make_admin: checked as boolean })}
              />
              <Label htmlFor="make-admin">Grant admin privileges</Label>
            </div>
            <div>
              <Label>Reason (optional)</Label>
              <Input
                placeholder="Reason for promotion..."
                value={promotionData.reason || ''}
                onChange={(e) => setPromotionData({ ...promotionData, reason: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setPromoteDialog({ open: false });
              setPromotionData({});
            }}>
              Cancel
            </Button>
            <Button onClick={handlePromote}>
              Promote User
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={deleteDialog.open} onOpenChange={(open) => setDeleteDialog({ open })}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Delete User</DialogTitle>
            <DialogDescription>
              Archive {deleteDialog.user?.first_name} {deleteDialog.user?.last_name}? This action can be reversed.
            </DialogDescription>
          </DialogHeader>
          
          {deleteDialog.impact && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="flex items-start gap-2">
                <AlertTriangle className="h-5 w-5 text-yellow-600 mt-0.5" />
                <div className="flex-1">
                  <h4 className="font-semibold text-yellow-800 mb-2">Deletion Impact</h4>
                  {deleteDialog.user?.role === 'teacher' && (
                    <ul className="text-sm text-yellow-700 space-y-1">
                      <li>• {deleteDialog.impact.affected_classrooms} classrooms will be affected</li>
                      <li>• {deleteDialog.impact.affected_assignments} assignments created by this teacher</li>
                      <li>• {deleteDialog.impact.affected_students} students enrolled in their classrooms</li>
                    </ul>
                  )}
                  {deleteDialog.user?.role === 'student' && (
                    <ul className="text-sm text-yellow-700 space-y-1">
                      <li>• Enrolled in {deleteDialog.impact.enrolled_classrooms} classrooms</li>
                      <li>• Has {deleteDialog.impact.total_assignments} assignments</li>
                      <li>• Completed {deleteDialog.impact.test_attempts} test attempts</li>
                    </ul>
                  )}
                </div>
              </div>
            </div>
          )}
          
          <div className="space-y-4">
            <div>
              <Label>Reason for deletion</Label>
              <Select
                value={deletionData.reason}
                onValueChange={(value) => setDeletionData({ ...deletionData, reason: value as any })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="graduation">Graduation</SelectItem>
                  <SelectItem value="transfer">Transfer</SelectItem>
                  <SelectItem value="disciplinary">Disciplinary</SelectItem>
                  <SelectItem value="inactive">Inactive</SelectItem>
                  <SelectItem value="other">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            {deletionData.reason === 'other' && (
              <div>
                <Label>Custom reason</Label>
                <Input
                  placeholder="Please specify..."
                  value={deletionData.custom_reason || ''}
                  onChange={(e) => setDeletionData({ ...deletionData, custom_reason: e.target.value })}
                />
              </div>
            )}
            
            {deleteDialog.user?.role === 'student' && (
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="notify-teachers"
                  checked={deletionData.notify_affected_teachers ?? false}
                  onCheckedChange={(checked) => setDeletionData({ ...deletionData, notify_affected_teachers: checked as boolean })}
                />
                <Label htmlFor="notify-teachers">Notify affected teachers</Label>
              </div>
            )}
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialog({ open: false })}>
              Cancel
            </Button>
            {deleteDialog.user?.role === 'student' && (
              <Button
                variant="destructive"
                onClick={() => {
                  setHardDeleteDialog({ open: true, user: deleteDialog.user });
                  setDeleteDialog({ open: false });
                }}
              >
                Permanent Delete
              </Button>
            )}
            <Button onClick={handleSoftDelete}>
              Archive User
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Hard Delete Dialog */}
      <Dialog open={hardDeleteDialog.open} onOpenChange={(open) => setHardDeleteDialog({ open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-red-600">Permanent Deletion Warning</DialogTitle>
            <DialogDescription>
              This will permanently delete all data for {hardDeleteDialog.user?.first_name} {hardDeleteDialog.user?.last_name}.
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-sm text-red-800">
              To confirm, please type: <strong>PERMANENTLY DELETE {hardDeleteDialog.user?.first_name} {hardDeleteDialog.user?.last_name}</strong>
            </p>
          </div>
          
          <div>
            <Input
              placeholder="Type confirmation phrase..."
              value={confirmationPhrase}
              onChange={(e) => setConfirmationPhrase(e.target.value)}
              className="font-mono"
            />
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setHardDeleteDialog({ open: false })}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleHardDelete}
              disabled={confirmationPhrase !== `PERMANENTLY DELETE ${hardDeleteDialog.user?.first_name} ${hardDeleteDialog.user?.last_name}`}
            >
              Permanently Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Name Dialog */}
      <Dialog open={editNameDialog.open} onOpenChange={(open) => setEditNameDialog({ open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit User Name</DialogTitle>
            <DialogDescription>
              Update the name for {editNameDialog.user?.email}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="first-name">First Name</Label>
              <Input
                id="first-name"
                value={nameEditData.first_name}
                onChange={(e) => setNameEditData({ ...nameEditData, first_name: e.target.value })}
                placeholder="Enter first name"
                maxLength={100}
              />
            </div>
            <div>
              <Label htmlFor="last-name">Last Name</Label>
              <Input
                id="last-name"
                value={nameEditData.last_name}
                onChange={(e) => setNameEditData({ ...nameEditData, last_name: e.target.value })}
                placeholder="Enter last name"
                maxLength={100}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setEditNameDialog({ open: false });
              setNameEditData({ first_name: '', last_name: '' });
            }}>
              Cancel
            </Button>
            <Button 
              onClick={handleUpdateName}
              disabled={!nameEditData.first_name.trim() || !nameEditData.last_name.trim()}
            >
              Update Name
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}