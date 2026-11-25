import { useState, useMemo } from 'react';
import { Header } from '../components/Header';
import { StatusBadge } from '../components/StatusBadge';
import { StatCard } from '../components/StatCard';
import { Database, CheckCircle, AlertTriangle, Copy, X, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';

interface LedgerRecord {
  blockNumber: number;
  txHash: string;
  recordType: 'ENROLLMENT' | 'PAYMENT' | 'DELIVERY' | 'CONTRACT';
  entityId: string;
  entityName: string;
  writtenAt: string;
  verificationStatus: 'CONFIRMED' | 'PENDING' | 'FAILED';
  mysqlMatch: 'MATCH' | 'MISMATCH';
}

const mockRecords: LedgerRecord[] = [
  {
    blockNumber: 45892,
    txHash: '0x7f3a9b2c45d8e1f7890abcdef1234567890abcdef1234567890abcdef1234567',
    recordType: 'PAYMENT',
    entityId: 'TXN-2026-78451',
    entityName: 'M-Pesa #7842 → Kilimani Primary',
    writtenAt: '2026-05-12 14:23:18',
    verificationStatus: 'CONFIRMED',
    mysqlMatch: 'MATCH',
  },
  {
    blockNumber: 45891,
    txHash: '0x4c2d1a8f67e9b3c5890def1234567890abcdef1234567890abcdef1234567890',
    recordType: 'ENROLLMENT',
    entityId: 'STU-45892',
    entityName: 'John Doe - Kilimani Primary',
    writtenAt: '2026-05-12 13:45:22',
    verificationStatus: 'CONFIRMED',
    mysqlMatch: 'MATCH',
  },
  {
    blockNumber: 45890,
    txHash: '0x1a2b3c4d5e6f7890123456789abcdef0123456789abcdef0123456789abcdef0',
    recordType: 'PAYMENT',
    entityId: 'TXN-2026-78450',
    entityName: 'Subsidy Grant → Olympic Primary',
    writtenAt: '2026-05-12 12:15:04',
    verificationStatus: 'CONFIRMED',
    mysqlMatch: 'MATCH',
  },
  {
    blockNumber: 45889,
    txHash: '0x9e8d7c6b5a4f3210fedcba9876543210fedcba9876543210fedcba9876543210',
    recordType: 'DELIVERY',
    entityId: 'DEL-2026-0982',
    entityName: 'Maize Flour Delivery → Kibera Heroes',
    writtenAt: '2026-05-12 11:30:19',
    verificationStatus: 'CONFIRMED',
    mysqlMatch: 'MATCH',
  },
  {
    blockNumber: 45888,
    txHash: '0xbcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789a',
    recordType: 'CONTRACT',
    entityId: 'SC-2026-0044',
    entityName: 'Smart Contract Escrow Release #44',
    writtenAt: '2026-05-12 10:48:55',
    verificationStatus: 'CONFIRMED',
    mysqlMatch: 'MATCH',
  },
  {
    blockNumber: 45887,
    txHash: '0x3344556677889900aabbccddeeff00112233445566778899aabbccddeeff0011',
    recordType: 'PAYMENT',
    entityId: 'TXN-2026-78449',
    entityName: 'Supplier Direct → Highland Millers',
    writtenAt: '2026-05-12 10:12:33',
    verificationStatus: 'CONFIRMED',
    mysqlMatch: 'MATCH',
  },
  {
    blockNumber: 45886,
    txHash: '0x5566778899001122aabbccddeeff00112233445566778899aabbccddeeff0022',
    recordType: 'ENROLLMENT',
    entityId: 'STU-45893',
    entityName: 'Amina Hassan - Garissa Primary',
    writtenAt: '2026-05-12 09:55:10',
    verificationStatus: 'CONFIRMED',
    mysqlMatch: 'MATCH',
  },
  {
    blockNumber: 45885,
    txHash: '0x7788990011223344aabbccddeeff00112233445566778899aabbccddeeff0033',
    recordType: 'PAYMENT',
    entityId: 'TXN-2026-78448',
    entityName: 'M-Pesa Bulk → Turkana North Central',
    writtenAt: '2026-05-12 09:20:41',
    verificationStatus: 'CONFIRMED',
    mysqlMatch: 'MATCH',
  },
  {
    blockNumber: 45884,
    txHash: '0x9900112233445566aabbccddeeff00112233445566778899aabbccddeeff0044',
    recordType: 'DELIVERY',
    entityId: 'DEL-2026-0981',
    entityName: 'Milk Batch 400L → St. Teresa Academy',
    writtenAt: '2026-05-12 08:44:00',
    verificationStatus: 'CONFIRMED',
    mysqlMatch: 'MATCH',
  },
  {
    blockNumber: 45883,
    txHash: '0xbbccddeeff0011223344556677889900aabbccddeeff00112233445566778899',
    recordType: 'PAYMENT',
    entityId: 'TXN-2026-78447',
    entityName: 'Subsidy Disbursement → Jamhuri Academy',
    writtenAt: '2026-05-12 08:10:15',
    verificationStatus: 'CONFIRMED',
    mysqlMatch: 'MATCH',
  },
  {
    blockNumber: 45882,
    txHash: '0xddeeff00112233445566778899001122aabbccddeeff001122334455667788aa',
    recordType: 'CONTRACT',
    entityId: 'SC-2026-0043',
    entityName: 'Multi-Sig Approval Threshold #12',
    writtenAt: '2026-05-12 07:35:50',
    verificationStatus: 'CONFIRMED',
    mysqlMatch: 'MATCH',
  },
  {
    blockNumber: 45881,
    txHash: '0xff001122334455667788990011223344aabbccddeeff001122334455667788bb',
    recordType: 'PAYMENT',
    entityId: 'TXN-2026-78446',
    entityName: 'Supplier Cheque → Rift Agro Inputs',
    writtenAt: '2026-05-12 07:05:12',
    verificationStatus: 'CONFIRMED',
    mysqlMatch: 'MATCH',
  },
  {
    blockNumber: 45880,
    txHash: '0x11223344556677889900112233445566aabbccddeeff001122334455667788cc',
    recordType: 'ENROLLMENT',
    entityId: 'STU-45894',
    entityName: 'Brian Kiprop - Eldoret Town Day',
    writtenAt: '2026-05-12 06:40:22',
    verificationStatus: 'CONFIRMED',
    mysqlMatch: 'MATCH',
  },
  {
    blockNumber: 45879,
    txHash: '0x33445566778899001122334455667788aabbccddeeff001122334455667788dd',
    recordType: 'PAYMENT',
    entityId: 'TXN-2026-78445',
    entityName: 'M-Pesa Merchant → Coastal Food Hub',
    writtenAt: '2026-05-12 06:15:39',
    verificationStatus: 'CONFIRMED',
    mysqlMatch: 'MATCH',
  },
  {
    blockNumber: 45878,
    txHash: '0x55667788990011223344556677889900aabbccddeeff001122334455667788ee',
    recordType: 'DELIVERY',
    entityId: 'DEL-2026-0980',
    entityName: 'Beans Ration 500KG → Kisumu Day',
    writtenAt: '2026-05-12 05:50:08',
    verificationStatus: 'CONFIRMED',
    mysqlMatch: 'MATCH',
  },
  {
    blockNumber: 45877,
    txHash: '0x77889900112233445566778899001122aabbccddeeff001122334455667788ff',
    recordType: 'PAYMENT',
    entityId: 'TXN-2026-78444',
    entityName: 'Porridge Grain Grant → Wajir West Primary',
    writtenAt: '2026-05-12 05:25:44',
    verificationStatus: 'CONFIRMED',
    mysqlMatch: 'MATCH',
  },
  {
    blockNumber: 45876,
    txHash: '0x99001122334455667788990011223344aabbccddeeff00112233445566778800',
    recordType: 'CONTRACT',
    entityId: 'SC-2026-0042',
    entityName: 'Automated Fraud Freeze Assertion',
    writtenAt: '2026-05-12 04:55:12',
    verificationStatus: 'CONFIRMED',
    mysqlMatch: 'MATCH',
  },
  {
    blockNumber: 45875,
    txHash: '0xbbccddeeff0011223344556677889900aabbccddeeff00112233445566778811',
    recordType: 'PAYMENT',
    entityId: 'TXN-2026-78443',
    entityName: 'Direct Transfer → Machakos Comprehensive',
    writtenAt: '2026-05-12 04:20:30',
    verificationStatus: 'CONFIRMED',
    mysqlMatch: 'MATCH',
  },
  {
    blockNumber: 45874,
    txHash: '0xddeeff00112233445566778899001122aabbccddeeff00112233445566778822',
    recordType: 'ENROLLMENT',
    entityId: 'STU-45895',
    entityName: 'Faith Wanjiku - Nyeri Boarding',
    writtenAt: '2026-05-12 03:50:18',
    verificationStatus: 'CONFIRMED',
    mysqlMatch: 'MATCH',
  },
  {
    blockNumber: 45873,
    txHash: '0xff001122334455667788990011223344aabbccddeeff00112233445566778833',
    recordType: 'PAYMENT',
    entityId: 'TXN-2026-78442',
    entityName: 'Off-Hours Treasury Flagged Payment',
    writtenAt: '2026-05-12 02:30:00',
    verificationStatus: 'PENDING',
    mysqlMatch: 'MISMATCH',
  },
  {
    blockNumber: 45872,
    txHash: '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
    recordType: 'DELIVERY',
    entityId: 'DEL-2026-0979',
    entityName: 'Rice Consignment → Isiolo Central',
    writtenAt: '2026-05-12 01:45:15',
    verificationStatus: 'CONFIRMED',
    mysqlMatch: 'MATCH',
  },
  {
    blockNumber: 45871,
    txHash: '0x234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1',
    recordType: 'PAYMENT',
    entityId: 'TXN-2026-78441',
    entityName: 'Midnight Subsidy Surge → Bomet Central',
    writtenAt: '2026-05-12 01:10:05',
    verificationStatus: 'CONFIRMED',
    mysqlMatch: 'MATCH',
  },
];

export function BlockchainLedger() {
  const [selectedRecord, setSelectedRecord] = useState<LedgerRecord | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [recordTypeFilter, setRecordTypeFilter] = useState<string>('ALL');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const pageSize = 15; // Max 15 per page

  const filteredRecords = useMemo(() => {
    return mockRecords.filter(record => {
      const matchesType = recordTypeFilter === 'ALL' || record.recordType === recordTypeFilter;
      const q = searchQuery.trim().toLowerCase();
      const matchesSearch =
        !q ||
        record.entityId.toLowerCase().includes(q) ||
        record.entityName.toLowerCase().includes(q) ||
        record.txHash.toLowerCase().includes(q) ||
        record.blockNumber.toString().includes(q);
      return matchesType && matchesSearch;
    });
  }, [searchQuery, recordTypeFilter]);

  const totalPages = Math.max(1, Math.ceil(filteredRecords.length / pageSize));
  const paginatedRecords = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredRecords.slice(start, start + pageSize);
  }, [filteredRecords, currentPage, pageSize]);

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <Header breadcrumbs={['Blockchain Ledger']} />

      <main className="flex-1 overflow-y-auto bg-[#F4F6F9] p-6">
        {/* Summary cards */}
        <div className="grid grid-cols-5 gap-4 mb-6">
          <StatCard icon={Database} label="Total Records on Ledger" value="1.2M" />
          <StatCard label="Last Block Written" value="2 mins ago" />
          <StatCard icon={CheckCircle} label="Ledger Sync Status" value="HEALTHY" />
          <StatCard label="Smart Contract Executions" value="2,847" />
          <StatCard icon={AlertTriangle} label="Tamper Attempts" value={0} />
        </div>

        {/* Search bar */}
        <div className="bg-white rounded-lg border border-[#DDE1E7] p-4 mb-6">
          <div className="flex gap-4">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              placeholder="Search by Entity ID, Transaction Hash, or Block Number..."
              className="flex-1 border border-[#DDE1E7] rounded px-4 py-2 text-sm"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => {
                  setSearchQuery('');
                  setCurrentPage(1);
                }}
                className="text-xs text-[#6B7280] hover:text-[#1C1C1E] px-2"
              >
                Clear
              </button>
            )}
          </div>
          <div className="flex gap-2 mt-3">
            {[
              { label: 'All Records', value: 'ALL' },
              { label: 'Payments', value: 'PAYMENT' },
              { label: 'Enrollments', value: 'ENROLLMENT' },
              { label: 'Deliveries', value: 'DELIVERY' },
              { label: 'Smart Contracts', value: 'CONTRACT' },
            ].map((tab) => (
              <button
                key={tab.value}
                type="button"
                onClick={() => {
                  setRecordTypeFilter(tab.value);
                  setCurrentPage(1);
                }}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  recordTypeFilter === tab.value
                    ? 'bg-[#1A3C5E] text-white'
                    : 'bg-[#F4F6F9] text-[#374151] hover:bg-[#DDE1E7]'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Ledger table */}
        <div className="bg-white rounded-lg border border-[#DDE1E7] overflow-hidden mb-6 shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-[#F4F6F9] border-b border-[#DDE1E7]">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#6B7280] uppercase tracking-wide">
                    Block Number
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#6B7280] uppercase tracking-wide">
                    Transaction Hash
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#6B7280] uppercase tracking-wide">
                    Record Type
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#6B7280] uppercase tracking-wide">
                    Entity
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#6B7280] uppercase tracking-wide">
                    Written At
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#6B7280] uppercase tracking-wide">
                    Verification
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#6B7280] uppercase tracking-wide">
                    MySQL Match
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#6B7280] uppercase tracking-wide">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {paginatedRecords.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="text-center py-8 text-[#6B7280] text-sm">
                      No ledger records found matching query.
                    </td>
                  </tr>
                ) : (
                  paginatedRecords.map((record, index) => (
                    <tr
                      key={record.blockNumber}
                      className={`border-b border-[#DDE1E7] hover:bg-[#F4F6F9] cursor-pointer ${
                        index % 2 === 0 ? 'bg-white' : 'bg-[#FAFAFA]'
                      }`}
                      onClick={() => setSelectedRecord(record)}
                    >
                      <td className="px-4 py-3 text-sm font-mono">{record.blockNumber}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono text-[#6B7280]">
                            {record.txHash.substring(0, 10)}...{record.txHash.substring(record.txHash.length - 6)}
                          </span>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              navigator.clipboard.writeText(record.txHash);
                            }}
                            className="p-1 hover:bg-[#F4F6F9] rounded"
                            title="Copy Hash"
                          >
                            <Copy className="w-3 h-3 text-[#6B7280]" />
                          </button>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-[#2471A3] text-white">
                          {record.recordType}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div>
                          <p className="text-sm font-medium">{record.entityName}</p>
                          <p className="text-xs text-[#6B7280] font-mono">{record.entityId}</p>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-xs font-mono text-[#6B7280]">
                        {record.writtenAt}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={record.verificationStatus} variant="filled" />
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge
                          status={record.mysqlMatch}
                          variant={record.mysqlMatch === 'MISMATCH' ? 'filled' : 'outline'}
                        />
                      </td>
                      <td className="px-4 py-3">
                        <button className="text-[#1A3C5E] hover:text-[#2E7D52] text-sm font-medium">
                          View
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls (Max 15 items per page) */}
          <div className="border-t border-[#DDE1E7] bg-white px-4 py-3 flex flex-col sm:flex-row items-center justify-between gap-3 text-sm">
            <div className="text-xs sm:text-sm text-[#6B7280]">
              {filteredRecords.length > 0 ? (
                <>
                  Showing{' '}
                  <span className="font-semibold text-[#1C1C1E]">
                    {(currentPage - 1) * pageSize + 1}
                  </span>{' '}
                  to{' '}
                  <span className="font-semibold text-[#1C1C1E]">
                    {Math.min(currentPage * pageSize, filteredRecords.length)}
                  </span>{' '}
                  of{' '}
                  <span className="font-semibold text-[#1C1C1E]">{filteredRecords.length}</span>{' '}
                  records
                  <span className="ml-2 text-xs text-[#9CA3AF]">(15 per page)</span>
                </>
              ) : (
                <span>No records to display</span>
              )}
            </div>

            <div className="flex items-center gap-1.5">
              {/* First Page */}
              <button
                type="button"
                onClick={() => setCurrentPage(1)}
                disabled={currentPage <= 1}
                title="First Page"
                className={`p-1.5 rounded border border-[#DDE1E7] flex items-center justify-center transition-colors ${
                  currentPage <= 1
                    ? 'text-[#9CA3AF] bg-[#F4F6F9] cursor-not-allowed'
                    : 'text-[#374151] hover:bg-[#F4F6F9] hover:text-[#1A3C5E]'
                }`}
              >
                <ChevronsLeft className="w-4 h-4" />
              </button>

              {/* Prev Page */}
              <button
                type="button"
                onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                disabled={currentPage <= 1}
                title="Previous Page"
                className={`px-2.5 py-1.5 rounded border border-[#DDE1E7] flex items-center gap-1 text-xs font-medium transition-colors ${
                  currentPage <= 1
                    ? 'text-[#9CA3AF] bg-[#F4F6F9] cursor-not-allowed'
                    : 'text-[#374151] hover:bg-[#F4F6F9] hover:text-[#1A3C5E]'
                }`}
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>Prev</span>
              </button>

              {/* Page Number Buttons */}
              <div className="flex items-center gap-1 mx-1">
                {Array.from({ length: totalPages }, (_, i) => i + 1)
                  .filter((pageNum) => {
                    if (totalPages <= 7) return true;
                    if (pageNum === 1 || pageNum === totalPages) return true;
                    return Math.abs(pageNum - currentPage) <= 1;
                  })
                  .reduce<(number | string)[]>((acc, pageNum, idx, arr) => {
                    if (idx > 0 && pageNum - (arr[idx - 1] as number) > 1) {
                      acc.push('...');
                    }
                    acc.push(pageNum);
                    return acc;
                  }, [])
                  .map((item, idx) => {
                    if (item === '...') {
                      return (
                        <span key={`ellipsis-${idx}`} className="px-2 py-1 text-xs text-[#9CA3AF]">
                          ...
                        </span>
                      );
                    }
                    const pageNum = item as number;
                    const isActive = pageNum === currentPage;
                    return (
                      <button
                        key={pageNum}
                        type="button"
                        onClick={() => setCurrentPage(pageNum)}
                        className={`min-w-[32px] h-8 px-2 rounded text-xs font-semibold transition-colors ${
                          isActive
                            ? 'bg-[#1A3C5E] text-white shadow-sm'
                            : 'border border-[#DDE1E7] text-[#374151] hover:bg-[#F4F6F9]'
                        }`}
                      >
                        {pageNum}
                      </button>
                    );
                  })}
              </div>

              {/* Next Page */}
              <button
                type="button"
                onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
                disabled={currentPage >= totalPages}
                title="Next Page"
                className={`px-2.5 py-1.5 rounded border border-[#DDE1E7] flex items-center gap-1 text-xs font-medium transition-colors ${
                  currentPage >= totalPages
                    ? 'text-[#9CA3AF] bg-[#F4F6F9] cursor-not-allowed'
                    : 'text-[#374151] hover:bg-[#F4F6F9] hover:text-[#1A3C5E]'
                }`}
              >
                <span>Next</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>

              {/* Last Page */}
              <button
                type="button"
                onClick={() => setCurrentPage(totalPages)}
                disabled={currentPage >= totalPages}
                title="Last Page"
                className={`p-1.5 rounded border border-[#DDE1E7] flex items-center justify-center transition-colors ${
                  currentPage >= totalPages
                    ? 'text-[#9CA3AF] bg-[#F4F6F9] cursor-not-allowed'
                    : 'text-[#374151] hover:bg-[#F4F6F9] hover:text-[#1A3C5E]'
                }`}
              >
                <ChevronsRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Block timeline */}
        <div className="bg-white rounded-lg border border-[#DDE1E7] p-6">
          <h3 className="font-bold text-lg mb-4">Recent Block Timeline</h3>
          <div className="flex gap-2 overflow-x-auto pb-4">
            {Array.from({ length: 20 }, (_, i) => {
              const blockNum = 45900 - i;
              const recordCount = Math.floor(Math.random() * 50) + 10;
              return (
                <div
                  key={blockNum}
                  className="flex-shrink-0 bg-[#F4F6F9] border border-[#DDE1E7] rounded-lg p-3 w-32 hover:bg-[#2471A3] hover:text-white cursor-pointer transition-colors group"
                >
                  <p className="text-xs font-mono mb-1">Block {blockNum}</p>
                  <p className="font-bold text-sm">{recordCount} records</p>
                  <p className="text-xs text-[#6B7280] group-hover:text-white/70">2 mins ago</p>
                </div>
              );
            })}
          </div>
        </div>
      </main>

      {/* Record Detail Modal */}
      {selectedRecord && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
          <div className="bg-white rounded-lg w-full max-w-3xl max-h-[90vh] overflow-y-auto shadow-2xl">
            <div className="sticky top-0 bg-white border-b border-[#DDE1E7] p-6 flex items-center justify-between">
              <div>
                <h2 className="font-bold text-xl">Ledger Record Details</h2>
                <p className="text-sm text-[#6B7280]">Block {selectedRecord.blockNumber}</p>
              </div>
              <button
                onClick={() => setSelectedRecord(null)}
                className="p-2 hover:bg-[#F4F6F9] rounded"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Transaction hash */}
              <div className="bg-[#F4F6F9] rounded-lg p-4">
                <h3 className="font-bold text-sm mb-2">Transaction Hash</h3>
                <div className="flex items-center gap-2">
                  <p className="text-xs font-mono text-[#6B7280] break-all">{selectedRecord.txHash}</p>
                  <button className="p-1.5 hover:bg-white rounded">
                    <Copy className="w-4 h-4 text-[#6B7280]" />
                  </button>
                </div>
              </div>

              {/* Record info */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h3 className="font-bold text-sm mb-2">Block Number</h3>
                  <p className="text-lg font-mono">{selectedRecord.blockNumber}</p>
                </div>
                <div>
                  <h3 className="font-bold text-sm mb-2">Record Type</h3>
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-[#2471A3] text-white">
                    {selectedRecord.recordType}
                  </span>
                </div>
                <div>
                  <h3 className="font-bold text-sm mb-2">Entity ID</h3>
                  <p className="font-mono text-sm">{selectedRecord.entityId}</p>
                </div>
                <div>
                  <h3 className="font-bold text-sm mb-2">Written At</h3>
                  <p className="text-sm">{selectedRecord.writtenAt}</p>
                </div>
              </div>

              {/* Verification panel */}
              <div className="bg-[#F4F6F9] rounded-lg p-4">
                <h3 className="font-bold text-sm mb-3">Verification Status</h3>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Blockchain Confirmation:</span>
                    <div className="flex items-center gap-2">
                      <CheckCircle className="w-4 h-4 text-[#2E7D52]" />
                      <StatusBadge status={selectedRecord.verificationStatus} variant="filled" />
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">MySQL Database Match:</span>
                    <StatusBadge
                      status={selectedRecord.mysqlMatch}
                      variant={selectedRecord.mysqlMatch === 'MISMATCH' ? 'filled' : 'outline'}
                    />
                  </div>
                </div>
              </div>

              {/* Raw payload */}
              <div>
                <h3 className="font-bold text-sm mb-2">Raw Payload (JSON)</h3>
                <div className="bg-[#1C1C1E] text-[#2E7D52] rounded-lg p-4 text-xs font-mono overflow-x-auto">
                  <pre>{JSON.stringify({
                    blockNumber: selectedRecord.blockNumber,
                    transactionHash: selectedRecord.txHash,
                    recordType: selectedRecord.recordType,
                    entityId: selectedRecord.entityId,
                    timestamp: selectedRecord.writtenAt,
                    verified: true
                  }, null, 2)}</pre>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
