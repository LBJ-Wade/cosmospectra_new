import numpy as np
from scipy import stats
from astropy import units as u
from . import useful_speedup

class Bispectrum:
    def __init__(self, box_dims, nGrid, dk=0.05):
        self.box_dims = box_dims
        self.nGrid    = nGrid
        self.Get_k(np.zeros((self.nGrid,self.nGrid,self.nGrid)), self.box_dims)
        self.Binned_k(dk=dk)
        self.data   = None

    def Get_k(self, data, box_dims):
        [kx,ky,kz],k = _get_k(data, box_dims)
        self.ks = {'kx': kx, 'ky': ky, 'kz': kz, 'k':k}

    def Binned_k(self, binned_k=None, dk=0.05):
        self.dk = dk
        if binned_k is None:
            bink = np.arange(self.ks['k'].min(), self.ks['k'].max(), self.dk)
            self.binned_k = bink[1:]/2.+bink[:-1]/2.
        else: self.binned_k = binned_k
        self.cube_k   = useful_speedup.put_nearest(self.ks['k'], self.binned_k)

    def Data(self, data=None, filename=None, file_reader=np.load):
        if data is None: data = file_reader(filename)
        self.data   = data
        self.dataft = np.fft.fftshift(np.fft.fftn(data.astype('float64')))

    def Calc_Bk_full(self):
        assert self.data is not None
        binned_N = self.binned_k.size
        self.Bks = np.zeros((binned_N,binned_N,binned_N))
        for p,k1 in enumerate(self.binned_k):
            Ifft1 = np.zeros_like(self.cube_k)
            Ifft1[np.abs(self.cube_k-k1)<self.dk/2] = 1
            dfft1 = self.dataft*Ifft1
            I1 = np.fft.ifftn(np.fft.fftshift(Ifft1))
            d1 = np.fft.ifftn(np.fft.fftshift(dfft1))
            for q,k2 in enumerate(self.binned_k):
                Ifft2 = np.zeros_like(self.cube_k)
                Ifft2[np.abs(self.cube_k-k2)<self.dk/2] = 1
                dfft2 = self.dataft*Ifft2
                I2 = np.fft.ifftn(np.fft.fftshift(Ifft2))
                d2 = np.fft.ifftn(np.fft.fftshift(dfft2))
                for r,k3 in enumerate(self.binned_k):
                    Ifft3 = np.zeros_like(self.cube_k)
                    Ifft3[np.abs(self.cube_k-k3)<self.dk/2] = 1
                    dfft3 = self.dataft*Ifft3
                    I3 = np.fft.ifftn(np.fft.fftshift(Ifft3))
                    d3 = np.fft.ifftn(np.fft.fftshift(dfft3))
                    
                    d123 = np.real(d1*d2*d3)
                    I123 = np.real(I1*I2*I3)
                    bk = np.sum(d123)/np.sum(I123)
                    self.Bks[p,q,r] = bk
                    count = p*binned_N*binned_N+q*binned_N+r+1
                    print(bk)
                    print('%d / %d'%(count,binned_N**3))

    def Calc_Bk_equilateral(self, binned_k=None, dk=0.05):
        assert self.data is not None
        if binned_k is not None: self.Binned_k(binned_k=binned_k, dk=dk)
        binned_N = self.binned_k.size
        Bks = np.zeros((binned_N))
        for p,k1 in enumerate(self.binned_k):
            Ifft1 = np.zeros_like(self.cube_k)
            Ifft1[np.abs(self.cube_k-k1)<self.dk/2] = 1
            dfft1 = self.dataft*Ifft1
            I1 = np.fft.ifftn(np.fft.fftshift(Ifft1))
            d1 = np.fft.ifftn(np.fft.fftshift(dfft1))
            d123 = np.real(d1*d1*d1)
            I123 = np.real(I1*I1*I1)
            bk = np.sum(d123)/np.sum(I123)
            Bks[p] = bk
            count = p+1
            print(bk)
            print('%d / %d'%(count,binned_N))
        return {'k': self.binned_k, 'Bk': Bks}

    def Bispec(self, data=None):
        if data is not None: self.Data(data=data)
        if data.shape[0]!=self.nGrid:
            self.nGrid = data.shape[0]
            self.Get_k(np.zeros((self.nGrid,self.nGrid,self.nGrid)), self.box_dims)
            self.Binned_k(dk=dk)
        self.Calc_Bk()
        return {'k': self.binned_k, 'Bk': self.Bks}


def round_nearest_float(n, num=0.5):
    return np.round(n/num)*num

def put_nearest(array, ref_list):
    fltn = np.array([array]) if type(array) in [int, float] else array.flatten()
    for i,ft in enumerate(fltn):
        fltn[i] = ref_list[np.abs(ref_list-ft).argmin()]
    return fltn.reshape(array.shape)

def _get_k(input_array, box_dims):
	'''
	Get the k values for input array with given dimensions.
	Return k components and magnitudes.
	For internal use.
	'''
	if np.array(box_dims).size!=3: box_dims = np.array([box_dims,box_dims,box_dims])
	dim = len(input_array.shape)
	if dim == 1:
		x = np.arange(len(input_array))
		center = x.max()/2.
		kx = 2.*np.pi*(x-center)/box_dims[0]
		return [kx], kx
	elif dim == 2:
		x,y = np.indices(input_array.shape, dtype='int32')
		center = np.array([(x.max()-x.min())/2, (y.max()-y.min())/2])
		kx = 2.*np.pi * (x-center[0])/box_dims[0]
		ky = 2.*np.pi * (y-center[1])/box_dims[1]
		k = np.sqrt(kx**2 + ky**2)
		return [kx, ky], k
	elif dim == 3:
		x,y,z = np.indices(input_array.shape, dtype='int32')
		center = np.array([(x.max()-x.min())/2, (y.max()-y.min())/2, \
						(z.max()-z.min())/2])
		kx = 2.*np.pi * (x-center[0])/box_dims[0]
		ky = 2.*np.pi * (y-center[1])/box_dims[1]
		kz = 2.*np.pi * (z-center[2])/box_dims[2]

		k = np.sqrt(kx**2 + ky**2 + kz**2 )
		return [kx,ky,kz], k