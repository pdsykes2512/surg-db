import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts';
import { useTableNavigation } from '../hooks/useTableNavigation';
import { PageHeader } from '../components/common/PageHeader'
import { Card } from '../components/common/Card'
import { Button } from '../components/common/Button'
import { PatientModal } from '../components/modals/PatientModal'
import { Table, TableHeader, TableBody, TableRow, TableHeadCell, TableCell } from '../components/common/Table'
import { Pagination } from '../components/common/Pagination'
import { usePagination } from '../hooks/usePagination'
import api from '../services/api';
import { formatDate } from '../utils/formatters';

interface Patient {
  _id: string;
  patient_id: string;
  mrn?: string;
  nhs_number?: string;
  episode_count?: number;
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

export function PatientsPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const searchInputRef = useRef<HTMLInputElement>(null);
  const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
  const [showModal, setShowModal] = useState(false);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [editingPatient, setEditingPatient] = useState<Patient | null>(null);
  const [deleteConfirmation, setDeleteConfirmation] = useState<{ show: boolean; patient: Patient | null }>({ show: false, patient: null });
  const [deleteConfirmText, setDeleteConfirmText] = useState('');

  // Keyboard shortcuts: Cmd+K to focus search, Cmd+Shift+P to add patient
  useKeyboardShortcuts({
    onFocusSearch: () => searchInputRef.current?.focus(),
    onAddPatient: () => {
      setEditingPatient(null);
      setShowModal(true);
    }
  });

  // Initialize pagination with auto-reset on search changes
  const pagination = usePagination({
    initialPageSize: 25,
    onFilterChange: [searchTerm]
  });

  const loadPatients = useCallback(async (search?: string) => {
    try {
      setLoading(true);
      setError(''); // Clear any previous errors
      const params = {
        search: search || undefined,
        skip: pagination.skip,
        limit: pagination.limit
      };

      // Count params should include search filter but not pagination
      const countParams = search ? { search } : {};

      // Parallel fetch for count and data
      const [countResponse, dataResponse] = await Promise.all([
        api.get('/patients/count', { params: countParams }),
        api.get('/patients/', { params }) // Add trailing slash for consistency
      ]);

      pagination.setTotalCount(countResponse.data.count);
      setPatients(dataResponse.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load patients');
    } finally {
      setLoading(false);
    }
  }, [pagination.skip, pagination.limit, pagination.setTotalCount]);

  useEffect(() => {
    loadPatients();
  }, [loadPatients]);

  // Debounce search to avoid too many API calls
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      loadPatients(searchTerm);
    }, 300); // Wait 300ms after user stops typing

    return () => clearTimeout(timeoutId);
  }, [searchTerm, loadPatients]);

  // Handle opening patient modal from navigation state (from HomePage activity or quick actions)
  useEffect(() => {
    const state = location.state as { openPatient?: string; addNew?: boolean }

    // Handle adding new patient from quick action
    if (state?.addNew) {
      setEditingPatient(null);
      setShowModal(true);
      // Clear the state to avoid reopening on refresh
      navigate(location.pathname, { replace: true, state: {} });
    }
    // Handle opening existing patient from activity
    else if (state?.openPatient && patients.length > 0) {
      const patient = patients.find(p => p.patient_id === state.openPatient)
      if (patient) {
        handleEdit(patient)
        // Clear the state to avoid reopening on refresh
        navigate(location.pathname, { replace: true, state: {} })
      }
    }
  }, [location.state, patients, location.pathname, navigate]);

  // Removed unused handleInputChange, formatNHSNumber, and handleNHSNumberChange functions

  const handleEdit = (patient: Patient) => {
    setEditingPatient(patient);
    setShowModal(true);
    setError('');
    setSuccess('');
  };

  const handleSubmit = async (data: PatientFormData) => {
    setError('');
    setSuccess('');

    try {
      setLoading(true);
      if (editingPatient) {
        // Update existing patient
        await api.put(`/patients/${editingPatient.patient_id}`, data);
        setSuccess('Patient updated successfully');
      } else {
        // Create new patient
        await api.post('/patients', data);
        setSuccess('Patient created successfully');
      }
      setShowModal(false);
      setEditingPatient(null);
      await loadPatients();
      // Clear error after successful load
      setError('');
    } catch (err: any) {
      setError(err.response?.data?.detail || `Failed to ${editingPatient ? 'update' : 'create'} patient`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteClick = (patient: Patient) => {
    setDeleteConfirmation({ show: true, patient });
    setDeleteConfirmText('');
    // Close the edit modal so delete confirmation appears on top
    setShowModal(false);
  };

  const handleDeleteConfirm = async () => {
    if (!deleteConfirmation.patient) return;
    
    // Verify user typed the correct record number
    if (deleteConfirmText !== deleteConfirmation.patient.patient_id) {
      setError('Record number does not match. Deletion cancelled.');
      return;
    }

    try {
      setLoading(true);
      await api.delete(`/patients/${deleteConfirmation.patient.patient_id}`);
      setSuccess(`Patient ${deleteConfirmation.patient.patient_id} deleted successfully`);
      setDeleteConfirmation({ show: false, patient: null });
      setDeleteConfirmText('');
      loadPatients();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete patient');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteConfirmation({ show: false, patient: null });
    setDeleteConfirmText('');
    setError('');
  };

  // No need for local filtering - backend handles search
  const filteredPatients = patients;

  // Table navigation: arrow keys, Enter to view, E to edit, Shift+D to delete, [/] for pagination
  const tableNav = useTableNavigation({
    items: filteredPatients,
    onView: (patient) => navigate(`/episodes/${patient.patient_id}`),
    onEdit: handleEdit,
    onDelete: handleDeleteClick,
    onPrevPage: () => pagination.handlePageChange(pagination.currentPage - 1),
    onNextPage: () => pagination.handlePageChange(pagination.currentPage + 1),
    canGoPrev: pagination.currentPage > 1,
    canGoNext: pagination.currentPage < pagination.totalPages,
    enabled: !showModal && !deleteConfirmation.show // Disable when modals are open
  });

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
          <Button
            variant="primary"
            className="w-full sm:w-auto"
            onClick={() => {
              setEditingPatient(null);
              setShowModal(true);
            }}
            keyboardHint={isMac ? '⌘⇧P' : 'Ctrl+Shift+P'}
          >
            + Add Patient
          </Button>
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

      {/* Search */}
      <Card>
        <div className="space-y-4">
          <div className="flex items-center space-x-4">
            <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <h3 className="text-lg font-semibold text-gray-900">Search</h3>
          </div>
          
          <div>
            <input
              ref={searchInputRef}
              type="text"
              placeholder="Search by Patient ID, MRN, or NHS Number..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full h-10 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {searchTerm && (
            <div className="flex justify-end">
              <Button
                variant="secondary"
                onClick={() => setSearchTerm('')}
              >
                Clear Search
              </Button>
            </div>
          )}
        </div>
      </Card>

      {/* Patient List */}
      <Card className="relative">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">Patient List</h2>
        </div>

        {/* Loading overlay - doesn't affect table layout */}
        {loading && (
          <div className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center z-10 rounded-lg">
            <div className="inline-flex items-center space-x-2">
              <svg className="animate-spin h-8 w-8 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span className="text-gray-600 font-medium">
                {searchTerm && (() => {
                  const clean = searchTerm.replace(/\s/g, '').toUpperCase();
                  // MRN patterns: 8+ digits, IW+6digits, or C+6digits+2alphanumeric
                  const isMrnOrNhs = /^\d{8,}$/.test(clean) || /^IW\d{6}$/.test(clean) || /^C\d{6}[A-Z0-9]{2}$/.test(clean);
                  return isMrnOrNhs ? 'Searching encrypted fields...' : 'Loading patients...';
                })()}
              </span>
            </div>
          </div>
        )}

        {patients.length === 0 && !loading && (
          <div className="text-center py-12">
            <svg className="mx-auto w-16 h-16 text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Patients Yet</h3>
            <p className="text-gray-500 mb-4">Get started by adding your first patient record</p>
          </div>
        )}
        {patients.length > 0 && filteredPatients.length === 0 && !loading && (
          <div className="text-center py-12">
            <svg className="mx-auto w-16 h-16 text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Patients Found</h3>
            <p className="text-gray-500 mb-4">No patients match your search: "{searchTerm}"</p>
            <Button variant="secondary" onClick={() => setSearchTerm('')}>
              Clear Search
            </Button>
          </div>
        )}
        {filteredPatients.length > 0 && (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHeadCell>Patient ID</TableHeadCell>
                <TableHeadCell>MRN</TableHeadCell>
                <TableHeadCell>NHS Number</TableHeadCell>
                <TableHeadCell>Date of Birth</TableHeadCell>
                <TableHeadCell>Episodes</TableHeadCell>
                <TableHeadCell>Actions</TableHeadCell>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredPatients.map((patient, index) => (
                <TableRow
                  key={patient._id}
                  onClick={() => navigate(`/episodes/${patient.patient_id}`)}
                  className={tableNav.selectedIndex === index ? 'ring-2 ring-blue-500 bg-blue-50' : ''}
                >
                  <TableCell className="font-medium text-gray-900">
                    {patient.patient_id}
                  </TableCell>
                  <TableCell className="text-gray-900">
                    {patient.mrn || '-'}
                  </TableCell>
                  <TableCell className="text-gray-900">
                    {patient.nhs_number}
                  </TableCell>
                  <TableCell className="text-gray-900">
                    {formatDate(patient.demographics.date_of_birth)}
                  </TableCell>
                  <TableCell className="text-gray-900">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      {patient.episode_count || 0}
                    </span>
                  </TableCell>
                  <TableCell className="text-gray-500">
                      <div className="flex items-center gap-3">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            handleEdit(patient)
                          }}
                          className="text-blue-600 hover:text-blue-800"
                          title="Edit patient"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                          </svg>
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            handleDeleteClick(patient)
                          }}
                          className="text-red-600 hover:text-red-800"
                          title="Delete patient"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}

        {/* Pagination */}
        {filteredPatients.length > 0 && (
          <Pagination
            currentPage={pagination.currentPage}
            totalItems={pagination.totalCount}
            pageSize={pagination.pageSize}
            onPageChange={pagination.handlePageChange}
            onPageSizeChange={pagination.handlePageSizeChange}
            loading={loading}
          />
        )}
      </Card>

      {/* Delete Confirmation Modal */}
      {deleteConfirmation.show && deleteConfirmation.patient && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="flex items-center gap-3">
                <div className="flex-shrink-0 w-12 h-12 rounded-full bg-red-100 flex items-center justify-center">
                  <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">Delete Patient Record</h3>
                  <p className="text-sm text-gray-500">This action cannot be undone</p>
                </div>
              </div>
            </div>
            <div className="px-6 py-4">
              <div className="mb-4">
                <p className="text-sm text-gray-700 mb-2">
                  You are about to permanently delete the patient record for:
                </p>
                <div className="bg-gray-50 rounded-md p-3 border border-gray-200">
                  <p className="text-sm font-medium text-gray-900">Record Number: {deleteConfirmation.patient.patient_id}</p>
                  <p className="text-sm text-gray-600">NHS Number: {deleteConfirmation.patient.nhs_number}</p>
                  <p className="text-sm text-gray-600">DOB: {formatDate(deleteConfirmation.patient.demographics.date_of_birth)}</p>
                </div>
              </div>
              
              <div className="bg-red-50 border border-red-200 rounded-md p-3 mb-4">
                <p className="text-sm font-medium text-red-800 mb-2">
                  ⚠️ Warning: This will permanently delete all patient data and cannot be recovered.
                </p>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  To confirm deletion, please type the patient's record number:
                  <span className="font-semibold text-red-600"> {deleteConfirmation.patient.patient_id}</span>
                </label>
                <input
                  type="text"
                  value={deleteConfirmText}
                  onChange={(e) => setDeleteConfirmText(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  placeholder="Enter record number to confirm"
                  autoFocus
                />
              </div>

              {error && deleteConfirmation.show && (
                <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded text-sm">
                  {error}
                </div>
              )}
            </div>
            <div className="px-6 py-4 bg-gray-50 rounded-b-lg flex justify-end gap-3">
              <Button
                type="button"
                variant="secondary"
                onClick={handleDeleteCancel}
                disabled={loading}
              >
                Cancel
              </Button>
              <Button
                type="button"
                variant="danger"
                onClick={handleDeleteConfirm}
                disabled={loading || deleteConfirmText !== deleteConfirmation.patient.patient_id}
              >
                {loading ? 'Deleting...' : 'Delete Patient'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Patient Modal */}
      {showModal && (
        <PatientModal
          patient={editingPatient}
          onClose={() => {
            setShowModal(false);
            setEditingPatient(null);
          }}
          onSubmit={handleSubmit}
          onDelete={handleDeleteClick}
          loading={loading}
        />
      )}
    </div>
  )
}


