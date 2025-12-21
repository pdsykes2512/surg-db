import { useState, useEffect } from 'react';
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { Button } from '../components/Button'
import api from '../services/api';

interface Patient {
  _id: string;
  record_number: string;
  nhs_number: string;
  demographics: {
    first_name: string;
    last_name: string;
    date_of_birth: string;
    age?: number;
    gender: string;
    ethnicity?: string;
    postcode?: string;
    bmi?: number;
    weight_kg?: number;
    height_cm?: number;
  };
  contact?: {
    phone?: string;
    email?: string;
  };
}

interface PatientFormData {
  record_number: string;
  nhs_number: string;
  demographics: {
    first_name: string;
    last_name: string;
    date_of_birth: string;
    age?: number;
    gender: string;
    ethnicity?: string;
    postcode?: string;
    bmi?: number;
    weight_kg?: number;
    height_cm?: number;
  };
  contact: {
    phone?: string;
    email?: string;
  };
  medical_history: {
    conditions: string[];
    previous_surgeries: any[];
    medications: string[];
    allergies: string[];
    smoking_status?: string;
    alcohol_use?: string;
  };
}

export function PatientsPage() {
  const [showForm, setShowForm] = useState(false);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  const [formData, setFormData] = useState<PatientFormData>({
    record_number: '',
    nhs_number: '',
    demographics: {
      first_name: '',
      last_name: '',
      date_of_birth: '',
      gender: 'male',
      ethnicity: '',
      postcode: '',
    },
    contact: {
      phone: '',
      email: '',
    },
    medical_history: {
      conditions: [],
      previous_surgeries: [],
      medications: [],
      allergies: [],
      smoking_status: 'never',
      alcohol_use: 'none',
    },
  });

  useEffect(() => {
    loadPatients();
  }, []);

  const loadPatients = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/patients');
      setPatients(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load patients');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (field: string, value: any) => {
    const keys = field.split('.');
    setFormData(prev => {
      const updated = { ...prev };
      let current: any = updated;
      for (let i = 0; i < keys.length - 1; i++) {
        current = current[keys[i]];
      }
      current[keys[keys.length - 1]] = value;
      return updated;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    
    try {
      setLoading(true);
      await api.post('/api/patients', formData);
      setSuccess('Patient created successfully');
      setShowForm(false);
      setFormData({
        record_number: '',
        nhs_number: '',
        demographics: {
          first_name: '',
          last_name: '',
          date_of_birth: '',
          gender: 'male',
          ethnicity: '',
          postcode: '',
        },
        contact: {
          phone: '',
          email: '',
        },
        medical_history: {
          conditions: [],
          previous_surgeries: [],
          medications: [],
          allergies: [],
          smoking_status: 'never',
          alcohol_use: 'none',
        },
      });
      loadPatients();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create patient');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Patient Management"
        subtitle="Manage patient records and demographics"
        icon={
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
          </svg>
        }
        action={
          !showForm ? (
            <Button variant="primary" onClick={() => setShowForm(true)}>+ Add Patient</Button>
          ) : (
            <Button variant="secondary" onClick={() => setShowForm(false)}>Cancel</Button>
          )
        }
      />

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          {error}
        </div>
      )}

      {success && (
        <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg text-green-700">
          {success}
        </div>
      )}

      {showForm && (
        <Card>
          <h2 className="text-xl font-semibold mb-4">New Patient</h2>
          <form onSubmit={handleSubmit}>
            {/* Basic Information */}
            <div className="mb-6">
              <h3 className="text-lg font-medium mb-3 text-gray-700">Basic Information</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Record Number <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    pattern="^\d{8}$|^IW\d{6}$"
                    title="Must be 8 digits or IW followed by 6 digits"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={formData.record_number}
                    onChange={(e) => handleInputChange('record_number', e.target.value)}
                  />
                  <p className="mt-1 text-xs text-gray-500">Format: 8 digits or IW + 6 digits (e.g., 12345678 or IW123456)</p>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    NHS Number <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    pattern="^\d{3} \d{3} \d{4}$"
                    title="Must be 10 digits formatted as XXX XXX XXXX"
                    placeholder="123 456 7890"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={formData.nhs_number}
                    onChange={(e) => handleInputChange('nhs_number', e.target.value)}
                  />
                  <p className="mt-1 text-xs text-gray-500">Format: XXX XXX XXXX (e.g., 123 456 7890)</p>
                </div>
              </div>
            </div>

            {/* Demographics */}
            <div className="mb-6">
              <h3 className="text-lg font-medium mb-3 text-gray-700">Demographics</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    First Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={formData.demographics.first_name}
                    onChange={(e) => handleInputChange('demographics.first_name', e.target.value)}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Last Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={formData.demographics.last_name}
                    onChange={(e) => handleInputChange('demographics.last_name', e.target.value)}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Date of Birth <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="date"
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={formData.demographics.date_of_birth}
                    onChange={(e) => handleInputChange('demographics.date_of_birth', e.target.value)}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Gender <span className="text-red-500">*</span>
                  </label>
                  <select
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={formData.demographics.gender}
                    onChange={(e) => handleInputChange('demographics.gender', e.target.value)}
                  >
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                    <option value="other">Other</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Postcode
                  </label>
                  <input
                    type="text"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={formData.demographics.postcode}
                    onChange={(e) => handleInputChange('demographics.postcode', e.target.value)}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Ethnicity
                  </label>
                  <input
                    type="text"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={formData.demographics.ethnicity}
                    onChange={(e) => handleInputChange('demographics.ethnicity', e.target.value)}
                  />
                </div>
              </div>
            </div>

            {/* Physical Measurements */}
            <div className="mb-6">
              <h3 className="text-lg font-medium mb-3 text-gray-700">Physical Measurements</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Weight (kg)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    min="20"
                    max="300"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={formData.demographics.weight_kg || ''}
                    onChange={(e) => handleInputChange('demographics.weight_kg', e.target.value ? parseFloat(e.target.value) : undefined)}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Height (cm)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    min="100"
                    max="250"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={formData.demographics.height_cm || ''}
                    onChange={(e) => handleInputChange('demographics.height_cm', e.target.value ? parseFloat(e.target.value) : undefined)}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    BMI
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    min="10"
                    max="80"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={formData.demographics.bmi || ''}
                    onChange={(e) => handleInputChange('demographics.bmi', e.target.value ? parseFloat(e.target.value) : undefined)}
                  />
                </div>
              </div>
            </div>

            {/* Contact Information */}
            <div className="mb-6">
              <h3 className="text-lg font-medium mb-3 text-gray-700">Contact Information</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Phone
                  </label>
                  <input
                    type="tel"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={formData.contact.phone}
                    onChange={(e) => handleInputChange('contact.phone', e.target.value)}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Email
                  </label>
                  <input
                    type="email"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={formData.contact.email}
                    onChange={(e) => handleInputChange('contact.email', e.target.value)}
                  />
                </div>
              </div>
            </div>

            <div className="flex gap-3">
              <Button type="submit" disabled={loading} variant="primary">
                {loading ? 'Creating...' : 'Create Patient'}
              </Button>
              <Button 
                type="button" 
                variant="secondary" 
                onClick={() => setShowForm(false)}
              >
                Cancel
              </Button>
            </div>
          </form>
        </Card>
      )}

      {/* Patient List */}
      <Card>
        <h2 className="text-xl font-semibold mb-4">Patient List</h2>
        {loading && !showForm && <p className="text-gray-500">Loading...</p>}
        {!loading && patients.length === 0 && (
          <div className="text-center py-12">
            <svg className="mx-auto w-16 h-16 text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Patients Yet</h3>
            <p className="text-gray-500 mb-4">Get started by adding your first patient record</p>
          </div>
        )}
        {patients.length > 0 && (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Record Number
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    NHS Number
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date of Birth
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Gender
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Postcode
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {patients.map((patient) => (
                  <tr key={patient._id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {patient.record_number}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {patient.nhs_number}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {patient.demographics.first_name} {patient.demographics.last_name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {patient.demographics.date_of_birth}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 capitalize">
                      {patient.demographics.gender}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {patient.demographics.postcode || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}

