import { useState, useEffect } from 'react'
import axios from 'axios'
import { useAuth } from '../contexts/AuthContext'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { Button } from '../components/Button'

const API_URL = 'http://localhost:8000'

interface User {
  _id: string
  email: string
  full_name: string
  role: string
  is_active: boolean
  department?: string
  job_title?: string
  created_at: string
}

interface Surgeon {
  _id: string
  first_name: string
  surname: string
  gmc_number?: string
  created_at: string
  updated_at: string
}

export function AdminPage() {
  const { token } = useAuth()
  const [activeTab, setActiveTab] = useState<'users' | 'surgeons'>('users')
  const [users, setUsers] = useState<User[]>([])
  const [surgeons, setSurgeons] = useState<Surgeon[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [showSurgeonForm, setShowSurgeonForm] = useState(false)
  const [editingSurgeon, setEditingSurgeon] = useState<Surgeon | null>(null)
  const [showPasswordModal, setShowPasswordModal] = useState(false)
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null)
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: '',
    role: 'viewer',
    department: '',
    job_title: ''
  })
  const [surgeonFormData, setSurgeonFormData] = useState({
    first_name: '',
    surname: '',
    gmc_number: ''
  })
  const [error, setError] = useState('')

  useEffect(() => {
    fetchUsers()
    fetchSurgeons()
  }, [])

  const fetchUsers = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/admin/users`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setUsers(response.data)
    } catch (err) {
      setError('Failed to fetch users')
    } finally {
      setLoading(false)
    }
  }

  const fetchSurgeons = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/admin/surgeons`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setSurgeons(response.data)
    } catch (err) {
      setError('Failed to fetch surgeons')
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    try {
      await axios.post(`${API_URL}/api/admin/users`, formData, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setShowForm(false)
      setFormData({
        email: '',
        password: '',
        full_name: '',
        role: 'viewer',
        department: '',
        job_title: ''
      })
      fetchUsers()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create user')
    }
  }

  const toggleUserStatus = async (userId: string, currentStatus: boolean) => {
    try {
      await axios.put(
        `${API_URL}/api/admin/users/${userId}`,
        { is_active: !currentStatus },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      fetchUsers()
    } catch (err) {
      setError('Failed to update user status')
    }
  }

  const deleteUser = async (userId: string) => {
    if (!confirm('Are you sure you want to delete this user?')) return

    try {
      await axios.delete(`${API_URL}/api/admin/users/${userId}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      fetchUsers()
    } catch (err) {
      setError('Failed to delete user')
    }
  }

  const openPasswordModal = (userId: string) => {
    setSelectedUserId(userId)
    setNewPassword('')
    setConfirmPassword('')
    setShowPasswordModal(true)
    setError('')
  }

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedUserId) return

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    try {
      await axios.put(
        `${API_URL}/api/admin/users/${selectedUserId}/password`,
        { password: newPassword },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      setShowPasswordModal(false)
      setNewPassword('')
      setConfirmPassword('')
      setSelectedUserId(null)
      alert('Password changed successfully')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to change password')
    }
  }

  const handleSurgeonSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    try {
      if (editingSurgeon) {
        await axios.put(
          `${API_URL}/api/admin/surgeons/${editingSurgeon._id}`,
          surgeonFormData,
          { headers: { Authorization: `Bearer ${token}` } }
        )
      } else {
        await axios.post(`${API_URL}/api/admin/surgeons`, surgeonFormData, {
          headers: { Authorization: `Bearer ${token}` }
        })
      }
      setShowSurgeonForm(false)
      setEditingSurgeon(null)
      setSurgeonFormData({ first_name: '', surname: '', gmc_number: '' })
      fetchSurgeons()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save surgeon')
    }
  }

  const deleteSurgeon = async (surgeonId: string) => {
    if (!confirm('Are you sure you want to delete this surgeon?')) return

    try {
      await axios.delete(`${API_URL}/api/admin/surgeons/${surgeonId}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      fetchSurgeons()
    } catch (err) {
      setError('Failed to delete surgeon')
    }
  }

  const openEditSurgeon = (surgeon: Surgeon) => {
    setEditingSurgeon(surgeon)
    setSurgeonFormData({
      first_name: surgeon.first_name,
      surname: surgeon.surname,
      gmc_number: surgeon.gmc_number || ''
    })
    setShowSurgeonForm(true)
    setError('')
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading users...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Administration"
        subtitle="Manage system users, surgeons, and settings"
        icon={
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
          </svg>
        }
      />

      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('users')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'users'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Users
          </button>
          <button
            onClick={() => setActiveTab('surgeons')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'surgeons'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Surgeons
          </button>
        </nav>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {/* Users Tab */}
      {activeTab === 'users' && (
        <>
          <div className="flex justify-end">
            <Button onClick={() => setShowForm(!showForm)} variant="primary">
              {showForm ? 'Cancel' : '+ Create User'}
            </Button>
          </div>

      {showForm && (
        <Card>
          <div className="border-b border-gray-200 pb-4 mb-4">
            <h3 className="text-lg font-medium text-gray-900">Create New User</h3>
          </div>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email <span className="text-red-500">*</span>
                </label>
                <input
                  type="email"
                  required
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="user@example.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Password <span className="text-red-500">*</span>
                </label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Minimum 8 characters"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Full Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={formData.full_name}
                  onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="John Doe"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Role <span className="text-red-500">*</span>
                </label>
                <select
                  value={formData.role}
                  onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="viewer">Viewer</option>
                  <option value="data_entry">Data Entry</option>
                  <option value="surgeon">Surgeon</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Department
                </label>
                <input
                  type="text"
                  value={formData.department}
                  onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="e.g., General Surgery"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Job Title
                </label>
                <input
                  type="text"
                  value={formData.job_title}
                  onChange={(e) => setFormData({ ...formData, job_title: e.target.value })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="e.g., Consultant Surgeon"
                />
              </div>
            </div>
            <div className="flex justify-end">
              <Button type="submit" variant="success">
                Create User
              </Button>
            </div>
          </form>
        </Card>
      )}

      <Card padding="none">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Email
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Role
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Department
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {users.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-sm text-gray-500">
                    No users found
                  </td>
                </tr>
              ) : (
                users.map((user) => (
                  <tr key={user._id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {user.full_name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {user.email}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800 capitalize">
                        {user.role.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {user.department || '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                          user.is_active
                            ? 'bg-green-100 text-green-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {user.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                      <Button
                        onClick={() => openPasswordModal(user._id)}
                        variant="outline"
                        size="small"
                      >
                        Change Password
                      </Button>
                      <Button
                        onClick={() => toggleUserStatus(user._id, user.is_active)}
                        variant="secondary"
                        size="small"
                      >
                        {user.is_active ? 'Deactivate' : 'Activate'}
                      </Button>
                      <Button
                        onClick={() => deleteUser(user._id)}
                        variant="danger"
                        size="small"
                      >
                        Delete
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>
        </>
      )}

      {/* Surgeons Tab */}
      {activeTab === 'surgeons' && (
        <>
          <div className="flex justify-end">
            <Button 
              onClick={() => {
                setEditingSurgeon(null)
                setSurgeonFormData({ first_name: '', surname: '', gmc_number: '' })
                setShowSurgeonForm(!showSurgeonForm)
                setError('')
              }} 
              variant="primary"
            >
              {showSurgeonForm ? 'Cancel' : '+ Add Surgeon'}
            </Button>
          </div>

          {showSurgeonForm && (
            <Card>
              <div className="border-b border-gray-200 pb-4 mb-4">
                <h3 className="text-lg font-medium text-gray-900">
                  {editingSurgeon ? 'Edit Surgeon' : 'Add New Surgeon'}
                </h3>
              </div>
              <form onSubmit={handleSurgeonSubmit} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      First Name <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      required
                      value={surgeonFormData.first_name}
                      onChange={(e) => setSurgeonFormData({ ...surgeonFormData, first_name: e.target.value })}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="John"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Surname <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      required
                      value={surgeonFormData.surname}
                      onChange={(e) => setSurgeonFormData({ ...surgeonFormData, surname: e.target.value })}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="Smith"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      GMC Number
                    </label>
                    <input
                      type="text"
                      value={surgeonFormData.gmc_number}
                      onChange={(e) => setSurgeonFormData({ ...surgeonFormData, gmc_number: e.target.value })}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="1234567"
                    />
                  </div>
                </div>
                <div className="flex justify-end">
                  <Button type="submit" variant="success">
                    {editingSurgeon ? 'Update Surgeon' : 'Add Surgeon'}
                  </Button>
                </div>
              </form>
            </Card>
          )}

          <Card padding="none">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Surname
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      First Name
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      GMC Number
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {surgeons.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-6 py-8 text-center text-sm text-gray-500">
                        No surgeons found
                      </td>
                    </tr>
                  ) : (
                    surgeons.map((surgeon) => (
                      <tr key={surgeon._id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {surgeon.surname}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {surgeon.first_name}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {surgeon.gmc_number || '—'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                          <Button
                            onClick={() => openEditSurgeon(surgeon)}
                            variant="outline"
                            size="small"
                          >
                            Edit
                          </Button>
                          <Button
                            onClick={() => deleteSurgeon(surgeon._id)}
                            variant="danger"
                            size="small"
                          >
                            Delete
                          </Button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}

      {/* Password Change Modal */}
      {showPasswordModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">Change User Password</h3>
            </div>
            <form onSubmit={handlePasswordChange} className="px-6 py-4">
              {error && (
                <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded text-sm">
                  {error}
                </div>
              )}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  New Password <span className="text-red-500">*</span>
                </label>
                <input
                  type="password"
                  required
                  minLength={6}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Enter new password (min 6 characters)"
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Confirm Password <span className="text-red-500">*</span>
                </label>
                <input
                  type="password"
                  required
                  minLength={6}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Re-enter new password"
                />
              </div>
              <div className="flex justify-end space-x-3">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => {
                    setShowPasswordModal(false)
                    setNewPassword('')
                    setConfirmPassword('')
                    setSelectedUserId(null)
                    setError('')
                  }}
                >
                  Cancel
                </Button>
                <Button type="submit" variant="primary">
                  Change Password
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
