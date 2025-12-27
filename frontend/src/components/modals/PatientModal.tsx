import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { Button } from '../common/Button'

interface Patient {
  _id: string;
  patient_id: string;
  mrn?: string;
  nhs_number?: string;
  demographics: {
    date_of_birth: string;
    age?: number;
    gender: string;
    ethnicity?: string;
    postcode?: string;
    bmi?: number;
    weight_kg?: number;
    height_cm?: number;
    deceased_date?: string;
  };
  medical_history?: {
    conditions: string[];
    previous_surgeries: any[];
    medications: string[];
    allergies: string[];
    smoking_status?: string;
    alcohol_use?: string;
  };
}

interface PatientFormData {
  patient_id: string;
  mrn?: string;
  nhs_number?: string;
  demographics: {
    date_of_birth: string;
    age?: number;
    gender: string;
    ethnicity?: string;
    postcode?: string;
    bmi?: number;
    weight_kg?: number;
    deceased_date?: string;
    height_cm?: number;
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

interface PatientModalProps {
  patient?: Patient | null;
  onClose: () => void;
  onSubmit: (data: PatientFormData) => void;
  onDelete?: (patient: Patient) => void;
  loading?: boolean;
}

export function PatientModal({ patient, onClose, onSubmit, onDelete, loading = false }: PatientModalProps) {
  // Generate a 6-character hex patient ID for new patients
  const generatePatientId = () => {
    return Math.random().toString(16).substring(2, 8).toUpperCase();
  };

  const [formData, setFormData] = useState<PatientFormData>({
    patient_id: patient ? patient.patient_id : generatePatientId(),
    mrn: '',
    nhs_number: '',
    demographics: {
      date_of_birth: '',
      gender: 'male',
      ethnicity: '',
      postcode: '',
      deceased_date: '',
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
  const [validationError, setValidationError] = useState<string>('');

  useEffect(() => {
    if (patient) {
      setFormData({
        patient_id: patient.patient_id,
        mrn: patient.mrn || '',
        nhs_number: patient.nhs_number || '',
        demographics: {
          date_of_birth: patient.demographics.date_of_birth,
          gender: patient.demographics.gender,
          ethnicity: patient.demographics.ethnicity || '',
          postcode: patient.demographics.postcode || '',
          bmi: patient.demographics.bmi,
          weight_kg: patient.demographics.weight_kg,
          height_cm: patient.demographics.height_cm,
          deceased_date: patient.demographics.deceased_date || '',
        },
        medical_history: patient.medical_history || {
          conditions: [],
          previous_surgeries: [],
          medications: [],
          allergies: [],
          smoking_status: 'never',
          alcohol_use: 'none',
        },
      });
    }
  }, [patient]);

  const handleInputChange = (field: string, value: any) => {
    const keys = field.split('.');
    if (keys.length === 1) {
      setFormData({ ...formData, [field]: value });
    } else if (keys.length === 2) {
      setFormData({
        ...formData,
        [keys[0]]: {
          ...(formData as any)[keys[0]],
          [keys[1]]: value,
        },
      });
    }
  };

  const handleNHSNumberChange = (value: string) => {
    const digits = value.replace(/\D/g, '');
    let formatted = digits;
    if (digits.length > 3) {
      formatted = digits.slice(0, 3) + ' ' + digits.slice(3);
    }
    if (digits.length > 6) {
      formatted = digits.slice(0, 3) + ' ' + digits.slice(3, 6) + ' ' + digits.slice(6, 10);
    }
    setFormData({ ...formData, nhs_number: formatted });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Validate that at least one of MRN or NHS number is provided
    const hasMRN = formData.mrn && formData.mrn.trim().length > 0;
    const hasNHS = formData.nhs_number && formData.nhs_number.replace(/\s/g, '').length === 10;

    if (!hasMRN && !hasNHS) {
      setValidationError('At least one of MRN or NHS Number must be provided');
      return;
    }

    setValidationError('');
    onSubmit(formData);
  };

  // Ensure modal root exists
  let modalRoot = document.getElementById('modal-root')
  if (!modalRoot) {
    modalRoot = document.createElement('div')
    modalRoot.setAttribute('id', 'modal-root')
    document.body.appendChild(modalRoot)
  }

  return createPortal(
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[100] p-4" style={{ margin: 0 }}>
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-4 flex justify-between items-center">
          <div>
            <h2 className="text-xl font-bold text-white">{patient ? 'Edit Patient' : 'New Patient'}</h2>
            {patient && <p className="text-blue-100 text-sm mt-1">{patient.patient_id}</p>}
          </div>
          <button
            onClick={onClose}
            className="text-white hover:text-gray-200 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          <form onSubmit={handleSubmit} id="patient-form">
            {/* Basic Information */}
            <div className="mb-6">
              <h3 className="text-lg font-medium mb-3 text-gray-700">Basic Information</h3>

              {/* Validation error message */}
              {validationError && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-md text-sm">
                  {validationError}
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Patient ID
                  </label>
                  <input
                    type="text"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50 text-gray-600 cursor-not-allowed"
                    value={formData.patient_id}
                    readOnly
                    disabled
                  />
                  <p className="mt-1 text-xs text-gray-500">Auto-generated internal database identifier</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    MRN <span className="text-orange-500">*</span>
                  </label>
                  <input
                    type="text"
                    pattern="^\d{8}$|^IW\d{6}$"
                    title="Must be 8 digits or IW followed by 6 digits"
                    placeholder="12345678 or IW123456"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={formData.mrn}
                    onChange={(e) => handleInputChange('mrn', e.target.value)}
                    readOnly={!!patient}
                    disabled={!!patient}
                  />
                  <p className="mt-1 text-xs text-gray-500">Format: 8 digits or IW + 6 digits</p>
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    NHS Number <span className="text-orange-500">*</span>
                  </label>
                  <input
                    type="text"
                    title="NHS Number will be formatted as XXX XXX XXXX"
                    placeholder="123 456 7890"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={formData.nhs_number}
                    onChange={(e) => handleNHSNumberChange(e.target.value)}
                    readOnly={!!patient}
                    disabled={!!patient}
                  />
                  <p className="mt-1 text-xs text-gray-500">Format: XXX XXX XXXX (e.g., 123 456 7890)</p>
                </div>

                <div className="md:col-span-2 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                  <p className="text-sm text-yellow-800">
                    <span className="font-medium text-orange-500">* At least one required:</span> You must provide either an MRN or NHS Number (or both).
                  </p>
                </div>
              </div>
            </div>

            {/* Demographics */}
            <div className="mb-6">
              <h3 className="text-lg font-medium mb-3 text-gray-700">Demographics</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
                    Deceased Date
                  </label>
                  <input
                    type="date"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={formData.demographics.deceased_date || ''}
                    onChange={(e) => handleInputChange('demographics.deceased_date', e.target.value)}
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

                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Ethnicity
                  </label>
                  <select
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={formData.demographics.ethnicity}
                    onChange={(e) => handleInputChange('demographics.ethnicity', e.target.value)}
                  >
                    <option value="">Select ethnicity</option>
                    <optgroup label="White">
                      <option value="English, Welsh, Scottish, Northern Irish or British">English, Welsh, Scottish, Northern Irish or British</option>
                      <option value="Irish">Irish</option>
                      <option value="Gypsy or Irish Traveller">Gypsy or Irish Traveller</option>
                      <option value="Roma">Roma</option>
                      <option value="Any other White background">Any other White background</option>
                    </optgroup>
                    <optgroup label="Mixed or Multiple ethnic groups">
                      <option value="White and Black Caribbean">White and Black Caribbean</option>
                      <option value="White and Black African">White and Black African</option>
                      <option value="White and Asian">White and Asian</option>
                      <option value="Any other Mixed or Multiple ethnic background">Any other Mixed or Multiple ethnic background</option>
                    </optgroup>
                    <optgroup label="Asian or Asian British">
                      <option value="Indian">Indian</option>
                      <option value="Pakistani">Pakistani</option>
                      <option value="Bangladeshi">Bangladeshi</option>
                      <option value="Chinese">Chinese</option>
                      <option value="Any other Asian background">Any other Asian background</option>
                    </optgroup>
                    <optgroup label="Black, Black British, Caribbean or African">
                      <option value="Caribbean">Caribbean</option>
                      <option value="African">African</option>
                      <option value="Any other Black, Black British, or Caribbean background">Any other Black, Black British, or Caribbean background</option>
                    </optgroup>
                    <optgroup label="Other ethnic group">
                      <option value="Arab">Arab</option>
                      <option value="Any other ethnic group">Any other ethnic group</option>
                    </optgroup>
                    <option value="Prefer not to say">Prefer not to say</option>
                  </select>
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
          </form>
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 px-6 py-4 bg-gray-50 flex justify-between">
          <div>
            {patient && onDelete && (
              <Button 
                type="button" 
                variant="danger" 
                onClick={() => onDelete(patient)}
              >
                Delete Patient
              </Button>
            )}
          </div>
          <div className="flex gap-3">
            <Button variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button 
              type="submit" 
              form="patient-form" 
              disabled={loading} 
              variant="primary"
            >
              {loading ? (patient ? 'Updating...' : 'Creating...') : (patient ? 'Update Patient' : 'Create Patient')}
            </Button>
          </div>
        </div>
      </div>
    </div>,
    modalRoot
  )
}
