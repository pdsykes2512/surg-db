import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import { useAuth } from '../contexts/AuthContext'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { Button } from '../components/Button'

const API_URL = import.meta.env.VITE_API_URL?.replace('/api', '') || 'http://localhost:8000'

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

interface Clinician {
  _id: string
  first_name: string
  surname: string
  gmc_number?: string
  subspecialty_leads?: string[]
  clinical_role?: string
  created_at: string
  updated_at: string
}

export function AdminPage() {
  const { token } = useAuth()
  const [activeTab, setActiveTab] = useState<'users' | 'clinicians' | 'exports'>('users')
  const [users, setUsers] = useState<User[]>([])
  const [clinicians, setClinicians] = useState<Clinician[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [showClinicianForm, setShowClinicianForm] = useState(false)
  const [editingClinician, setEditingClinician] = useState<Clinician | null>(null)
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
  const [clinicianFormData, setClinicianFormData] = useState({
    first_name: '',
    surname: '',
    gmc_number: '',
    subspecialty_leads: [] as string[],
    clinical_role: 'surgeon'
  })
  const [error, setError] = useState('')

  const fetchUsers = useCallback(async () => {
    if (!token) {
      setError('No authentication token found. Please log in again.')
      setLoading(false)
      return
    }
    try {
      setLoading(true)
      const response = await axios.get(`${API_URL}/api/admin/users`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setUsers(response.data)
      setError('')
    } catch (err: any) {
      console.error('Failed to fetch users:', err)
      if (err.response?.status === 401) {
        setError('Session expired. Please log in again.')
      } else {
        const errorMsg = err.response?.data?.detail || err.message || 'Failed to fetch users'
        setError(errorMsg)
      }
    } finally {
      setLoading(false)
    }
  }, [token])

  const fetchClinicians = useCallback(async () => {
    if (!token) return
    try {
      const response = await axios.get(`${API_URL}/api/admin/clinicians`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setClinicians(response.data)
      setError('')
    } catch (err: any) {
      console.error('Failed to fetch clinicians:', err)
      if (err.response?.status === 401) {
        setError('Session expired. Please log in again.')
      } else {
        const errorMsg = err.response?.data?.detail || err.message || 'Failed to fetch clinicians'
        setError(errorMsg)
      }
    }
  }, [token])

  useEffect(() => {
    if (token) {
      fetchUsers()
      fetchClinicians()
    }
  }, [token, fetchUsers, fetchClinicians])

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

  const handleClinicianSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    try {
      // Prepare data: convert empty GMC number to null
      const dataToSubmit = {
        ...clinicianFormData,
        gmc_number: clinicianFormData.gmc_number.trim() === '' ? null : clinicianFormData.gmc_number
      }
      
      if (editingClinician) {
        await axios.put(
          `${API_URL}/api/admin/clinicians/${editingClinician._id}`,
          dataToSubmit,
          { headers: { Authorization: `Bearer ${token}` } }
        )
      } else {
        await axios.post(`${API_URL}/api/admin/clinicians`, dataToSubmit, {
          headers: { Authorization: `Bearer ${token}` }
        })
      }
      setShowClinicianForm(false)
      setEditingClinician(null)
      setClinicianFormData({ first_name: '', surname: '', gmc_number: '', subspecialty_leads: [], clinical_role: 'surgeon' })
      fetchClinicians()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save clinician')
    }
  }

  const deleteClinician = async (clinicianId: string) => {
    if (!confirm('Are you sure you want to delete this clinician?')) return

    try {
      await axios.delete(`${API_URL}/api/admin/clinicians/${clinicianId}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      fetchClinicians()
    } catch (err) {
      setError('Failed to delete clinician')
    }
  }

  const openEditClinician = (clinician: Clinician) => {
    setEditingClinician(clinician)
    setClinicianFormData({
      first_name: clinician.first_name,
      surname: clinician.surname,
      gmc_number: clinician.gmc_number || '',
      subspecialty_leads: clinician.subspecialty_leads || [],
      clinical_role: clinician.clinical_role || 'surgeon'
    })
    setShowClinicianForm(true)
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
            onClick={() => setActiveTab('clinicians')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'clinicians'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Clinicians
          </button>
          <button
            onClick={() => setActiveTab('exports')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'exports'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Exports
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
                  <tr key={user._id} className="hover:bg-blue-50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {user.full_name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {user.email}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800 capitalize">
                        {user.role.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
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
      {activeTab === 'clinicians' && (
        <>
          <div className="flex justify-end">
            <Button 
              onClick={() => {
                setEditingClinician(null)
                setClinicianFormData({ first_name: '', surname: '', gmc_number: '', subspecialty_leads: [], clinical_role: 'surgeon' })
                setShowClinicianForm(!showClinicianForm)
                setError('')
              }} 
              variant="primary"
            >
              {showClinicianForm ? 'Cancel' : '+ Add Clinician'}
            </Button>
          </div>

          {showClinicianForm && (
            <Card>
              <div className="border-b border-gray-200 pb-4 mb-4">
                <h3 className="text-lg font-medium text-gray-900">
                  {editingClinician ? 'Edit Clinician' : 'Add New Clinician'}
                </h3>
              </div>
              <form onSubmit={handleClinicianSubmit} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      First Name <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      required
                      value={clinicianFormData.first_name}
                      onChange={(e) => setClinicianFormData({ ...clinicianFormData, first_name: e.target.value })}
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
                      value={clinicianFormData.surname}
                      onChange={(e) => setClinicianFormData({ ...clinicianFormData, surname: e.target.value })}
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
                      value={clinicianFormData.gmc_number}
                      onChange={(e) => setClinicianFormData({ ...clinicianFormData, gmc_number: e.target.value })}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="1234567"
                      pattern="[0-9]{7}"
                      maxLength={7}
                      title="GMC number must be exactly 7 digits"
                    />
                    <p className="mt-1 text-xs text-gray-500">7 digits only</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Clinical Role <span className="text-red-500">*</span>
                    </label>
                    <select
                      required
                      value={clinicianFormData.clinical_role}
                      onChange={(e) => setClinicianFormData({ ...clinicianFormData, clinical_role: e.target.value })}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      <option value="surgeon">Surgeon</option>
                      <option value="anaesthetist">Anaesthetist</option>
                      <option value="oncologist">Oncologist</option>
                      <option value="radiologist">Radiologist</option>
                      <option value="other">Other</option>
                    </select>
                  </div>
                </div>
                <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
                  <label className="block text-sm font-medium text-gray-900 mb-2">
                    Subspecialty Leads
                  </label>
                  <p className="text-xs text-gray-600 mb-3">
                    Select which cancer subspecialties this clinician can lead
                  </p>
                  <div className="grid grid-cols-2 gap-2">
                    {[
                      { value: 'colorectal', label: 'Colorectal' },
                      { value: 'urology', label: 'Urology' },
                      { value: 'breast', label: 'Breast' },
                      { value: 'upper_gi', label: 'Upper GI' },
                      { value: 'gynae_onc', label: 'Gynae Onc' },
                      { value: 'other', label: 'Other' }
                    ].map((subspecialty) => (
                      <label key={subspecialty.value} className="flex items-center space-x-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={clinicianFormData.subspecialty_leads.includes(subspecialty.value)}
                          onChange={(e) => {
                            const newLeads = e.target.checked
                              ? [...clinicianFormData.subspecialty_leads, subspecialty.value]
                              : clinicianFormData.subspecialty_leads.filter(s => s !== subspecialty.value)
                            setClinicianFormData({ ...clinicianFormData, subspecialty_leads: newLeads })
                          }}
                          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        />
                        <span className="text-sm text-gray-700">{subspecialty.label}</span>
                      </label>
                    ))}
                  </div>
                </div>
                <div className="flex justify-end">
                  <Button type="submit" variant="success">
                    {editingClinician ? 'Update Clinician' : 'Add Clinician'}
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
                      Role
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Subspecialty Leads
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {clinicians.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-6 py-8 text-center text-sm text-gray-500">
                        No clinicians found
                      </td>
                    </tr>
                  ) : (
                    clinicians.map((clinician) => (
                      <tr key={clinician._id} className="hover:bg-blue-50 transition-colors">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {clinician.surname}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {clinician.first_name}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {clinician.gmc_number || '—'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 capitalize">
                            {clinician.clinical_role || 'surgeon'}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-900">
                          {clinician.subspecialty_leads && clinician.subspecialty_leads.length > 0 ? (
                            <div className="flex flex-wrap gap-1">
                              {clinician.subspecialty_leads.map((lead) => (
                                <span key={lead} className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 capitalize">
                                  {lead.replace('_', ' ')}
                                </span>
                              ))}
                            </div>
                          ) : (
                            <span className="text-gray-400">—</span>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                          <Button
                            onClick={() => openEditClinician(clinician)}
                            variant="outline"
                            size="small"
                          >
                            Edit
                          </Button>
                          <Button
                            onClick={() => deleteClinician(clinician._id)}
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

      {/* Exports Tab */}
      {activeTab === 'exports' && (
        <>
          <Card>
            <div className="border-b border-gray-200 pb-4 mb-6">
              <h3 className="text-lg font-medium text-gray-900">NBOCA/COSD Data Export</h3>
              <p className="text-sm text-gray-600 mt-1">
                Export bowel cancer episode data in XML format for National Bowel Cancer Audit (NBOCA) submission.
              </p>
            </div>

            <div className="space-y-6">
              {/* Date Range Filter */}
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-medium text-gray-900">Date Range Filter (Optional)</h4>
                  <button
                    type="button"
                    onClick={() => {
                      (document.getElementById('export-start-date') as HTMLInputElement).value = '';
                      (document.getElementById('export-end-date') as HTMLInputElement).value = ''
                    }}
                    className="text-xs text-blue-600 hover:text-blue-800"
                  >
                    Clear Dates
                  </button>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Start Date (Diagnosis Date)
                    </label>
                    <input
                      type="date"
                      id="export-start-date"
                      className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      End Date (Diagnosis Date)
                    </label>
                    <input
                      type="date"
                      id="export-end-date"
                      className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                </div>
                <p className="text-xs text-gray-600 mt-2">
                  Leave dates empty to export all cancer episodes
                </p>
              </div>

              {/* Export Actions */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Button
                  variant="success"
                  onClick={async () => {
                    try {
                      const response = await axios.get(`${API_URL}/api/admin/exports/nboca-validator`, {
                        headers: { Authorization: `Bearer ${token}` }
                      })
                      
                      const data = response.data
                      const summary = data.summary
                      
                      // Create detailed report
                      let report = `🔍 NBOCA Submission Validator\n\n`
                      report += `📊 Summary:\n`
                      report += `Total Episodes: ${summary.total_episodes}\n`
                      report += `Valid Episodes: ${summary.valid_episodes} (${summary.valid_percentage}%)\n`
                      report += `Episodes with Errors: ${summary.episodes_with_errors}\n`
                      report += `Episodes with Warnings: ${summary.episodes_with_warnings}\n\n`
                      
                      if (summary.submission_ready) {
                        report += `✅ SUBMISSION READY - All episodes pass validation!\n\n`
                      } else {
                        report += `❌ NOT READY FOR SUBMISSION\n\n`
                        report += `Issues Found:\n\n`
                        
                        data.episodes.forEach((ep: any) => {
                          report += `Episode: ${ep.patient_id}\n`
                          
                          if (ep.errors.length > 0) {
                            report += `  ❌ Errors:\n`
                            ep.errors.forEach((err: string) => report += `     - ${err}\n`)
                          }
                          
                          if (ep.warnings.length > 0) {
                            report += `  ⚠️  Warnings:\n`
                            ep.warnings.forEach((warn: string) => report += `     - ${warn}\n`)
                          }
                          
                          report += `\n`
                        })
                      }
                      
                      alert(report)
                      setError('')
                    } catch (err: any) {
                      setError('Failed to validate data: ' + (err.response?.data?.detail || err.message))
                    }
                  }}
                >
                  🔍 Validate NBOCA Submission
                </Button>
                
                <Button
                  variant="primary"
                  onClick={async () => {
                    const startDate = (document.getElementById('export-start-date') as HTMLInputElement)?.value
                    const endDate = (document.getElementById('export-end-date') as HTMLInputElement)?.value
                    
                    try {
                      const params = new URLSearchParams()
                      if (startDate) params.append('start_date', startDate)
                      if (endDate) params.append('end_date', endDate)
                      
                      const url = `${API_URL}/api/admin/exports/nboca-xml${params.toString() ? '?' + params.toString() : ''}`
                      
                      const response = await axios.get(url, {
                        headers: { Authorization: `Bearer ${token}` },
                        responseType: 'blob'
                      })
                      
                      // Create download link
                      const blob = new Blob([response.data], { type: 'application/xml' })
                      const downloadUrl = window.URL.createObjectURL(blob)
                      const link = document.createElement('a')
                      link.href = downloadUrl
                      link.download = `nboca_export_${new Date().toISOString().split('T')[0]}.xml`
                      document.body.appendChild(link)
                      link.click()
                      link.remove()
                      window.URL.revokeObjectURL(downloadUrl)
                      
                      setError('')
                    } catch (err: any) {
                      if (err.response?.status === 404) {
                        const detail = err.response?.data?.detail || 'No episodes found'
                        setError(detail)
                      } else {
                        setError('Failed to generate export: ' + (err.response?.data?.detail || err.message))
                      }
                    }
                  }}
                >
                  📥 Download NBOCA XML
                </Button>

                <Button
                  variant="secondary"
                  onClick={async () => {
                    try {
                      const response = await axios.get(`${API_URL}/api/admin/exports/data-completeness`, {
                        headers: { Authorization: `Bearer ${token}` }
                      })
                      
                      const data = response.data
                      
                      // Format completeness report
                      let report = `NBOCA Data Completeness Report\n`
                      report += `Total Episodes: ${data.total_episodes}\n\n`
                      
                      report += `Patient Demographics:\n`
                      for (const [field, value] of Object.entries(data.patient_demographics)) {
                        if (typeof value === 'object' && value !== null) {
                          const v = value as { count: number; percentage: number }
                          report += `  ${field}: ${v.count}/${data.total_episodes} (${v.percentage}%)\n`
                        }
                      }
                      
                      report += `\nDiagnosis:\n`
                      for (const [field, value] of Object.entries(data.diagnosis)) {
                        if (typeof value === 'object' && value !== null) {
                          const v = value as { count: number; percentage: number }
                          report += `  ${field}: ${v.count}/${data.total_episodes} (${v.percentage}%)\n`
                        }
                      }
                      
                      const surgeryTotal = data.surgery.total_surgical_episodes
                      report += `\nSurgery (${surgeryTotal} surgical episodes):\n`
                      for (const [field, value] of Object.entries(data.surgery)) {
                        if (field !== 'total_surgical_episodes' && typeof value === 'object' && value !== null) {
                          const v = value as { count: number; percentage: number }
                          report += `  ${field}: ${v.count}/${surgeryTotal} (${v.percentage}%)\n`
                        }
                      }
                      
                      alert(report)
                      setError('')
                    } catch (err: any) {
                      setError('Failed to check data completeness: ' + (err.response?.data?.detail || err.message))
                    }
                  }}
                >
                  📊 Check Data Completeness
                </Button>
              </div>

              {/* Information */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h4 className="text-sm font-medium text-blue-900 mb-2">NBOCA Submission Tools</h4>
                <ul className="text-sm text-blue-800 space-y-1">
                  <li>• <strong>Validate:</strong> Check all episodes for NBOCA compliance before export</li>
                  <li>• <strong>Download XML:</strong> Export data in COSD v9/v10 format for NBOCA submission</li>
                  <li>• <strong>Check Completeness:</strong> View data completeness percentages</li>
                  <li>• Only bowel cancer episodes are included in validation and export</li>
                  <li>• Validation checks: mandatory fields, code formats, date logic, CRM for rectal cancers</li>
                </ul>
              </div>
            </div>
          </Card>
        </>
      )}
    </div>
  )
}
