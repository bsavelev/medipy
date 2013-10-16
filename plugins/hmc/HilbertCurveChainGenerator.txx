/*************************************************************************
 * MediPy - Copyright (C) Universite de Strasbourg
 * Distributed under the terms of the CeCILL-B license, as published by
 * the CEA-CNRS-INRIA. Refer to the LICENSE file or to
 * http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
 * for details.
 ************************************************************************/

#include "HilbertCurveChainGenerator.h"

#include <algorithm>
#include <vector>

#include <itkImageRegionConstIteratorWithIndex.h>
#include <vnl/vnl_matrix.h>
#include <vnl/vnl_vector.h>

template<typename TImage, typename TMask>
HilbertCurveChainGenerator<TImage, TMask>
::HilbertCurveChainGenerator()
{ 
    // Nothing to do.
}

template<typename TImage, typename TMask>
HilbertCurveChainGenerator<TImage, TMask>
::~HilbertCurveChainGenerator()
{
    // Nothing to do.
}

template<typename TImage, typename TMask>
void 
HilbertCurveChainGenerator<TImage, TMask>
::operator()(std::vector<ImageConstPointer> const & images, MaskConstPointer mask)
{
    //creation du parcours d'hilbert-peano
    this->m_Scan = this->_hilbert_peano_scan(this->_find_cube_length(images[0]));

    //gestion du masque+parcours de la chaine
    this->_image_scan(images, mask);
}

template<typename TImage, typename TMask>
typename HilbertCurveChainGenerator<TImage, TMask>::ImageChainsType const & 
HilbertCurveChainGenerator<TImage, TMask>
::GetImageChains() const
{
    return this->m_ImageChains;
}

template<typename TImage, typename TMask>
typename HilbertCurveChainGenerator<TImage, TMask>::MaskChainType const & 
HilbertCurveChainGenerator<TImage, TMask>
::GetMaskChain() const
{
    return this->m_MaskChain;
}

template<typename TImage, typename TMask>
typename HilbertCurveChainGenerator<TImage, TMask>::ScanConstPointer
HilbertCurveChainGenerator<TImage, TMask>
::GetScan() const
{
    return ScanConstPointer(this->m_Scan);
}

template<typename TImage, typename TMask>
unsigned int 
HilbertCurveChainGenerator<TImage, TMask>
::_find_cube_length(ImageType const * image)
{
    typename ImageType::SizeType const & size = 
        image->GetRequestedRegion().GetSize();
	
    //on cherche le max
    unsigned int const max = *std::max_element(size.m_Size, size.m_Size+size.GetSizeDimension());

    //trouver la plus petite puissance de 2 superieure à max
    unsigned int power=1;
    while(power<max)
    {
        power=power<<1;
    }

    return power;
}

template<typename TImage, typename TMask>
typename HilbertCurveChainGenerator<TImage, TMask>::ScanPointer
HilbertCurveChainGenerator<TImage, TMask>
::_hilbert_peano_scan(int cube_size)
{
    ScanPointer cube=ScanType::New();
    {
        ScanType::IndexType start; start.Fill(0);
        ScanType::SizeType size; size.Fill(cube_size);
        ScanType::RegionType region(start, size);
        cube->SetRegions(region);
        cube->Allocate();
    }

    //parcours de Peano dans un cube de taille 2
    if(cube_size==2)
    {
        ScanType::IndexType index;
        index[0] = 0; index[1] = 0; index[2] = 0; cube->SetPixel(index, 0);
        index[0] = 0; index[1] = 0; index[2] = 1; cube->SetPixel(index, 1);
        index[0] = 0; index[1] = 1; index[2] = 1; cube->SetPixel(index, 2);
        index[0] = 0; index[1] = 1; index[2] = 0; cube->SetPixel(index, 3);
        index[0] = 1; index[1] = 1; index[2] = 0; cube->SetPixel(index, 4);
        index[0] = 1; index[1] = 1; index[2] = 1; cube->SetPixel(index, 5);
        index[0] = 1; index[1] = 0; index[2] = 1; cube->SetPixel(index, 6);
        index[0] = 1; index[1] = 0; index[2] = 0; cube->SetPixel(index, 7);
    }
    else
    {
        //position (3D) d'insertion du cube de degre inferieur
        int iOrig=0,jOrig=0,kOrig=0;
        
        //position (dans la chaine) de Orig
        int posOrig=0;
        
        //nombre de voxels ds le cube
        int const nbVox=std::pow(cube_size, 3);
        
        //taille du sous-cube 
        int const sub_cube_size=cube_size/2;
        
        //nombre de voxels ds le sous-cube
        int const nbVoxInf=std::pow(sub_cube_size, 3);
        
        ScanPointer sub_cube = Self::_hilbert_peano_scan(sub_cube_size);
      
        typedef itk::ImageRegionConstIteratorWithIndex<ScanType> IteratorType;
        
        //calcul du demicube gauche (4 cubes de taille cube_size/2)
        for(IteratorType it(sub_cube, sub_cube->GetRequestedRegion());
            !it.IsAtEnd(); ++it)
        {
            ScanType::IndexType const & source=it.GetIndex();
            
            ScanType::IndexType destination;
            destination[0] = iOrig+source[2]; 
            destination[1] = jOrig+source[1];
            destination[2] = kOrig+source[0];
            
            cube->SetPixel(destination, posOrig+it.Get());
        }

        //definition du point d'insertion du prochain mini cube
        kOrig+=sub_cube_size;
		
        //maj du nombre de voxels inseres
        posOrig+=nbVoxInf;
        for(IteratorType it(sub_cube, sub_cube->GetRequestedRegion());
            !it.IsAtEnd(); ++it)
        {
            ScanType::IndexType const & source=it.GetIndex();
            
            ScanType::IndexType destination;
            destination[0] = iOrig+source[1]; 
            destination[1] = jOrig+source[0];
            destination[2] = kOrig+source[2];
            
            cube->SetPixel(destination, posOrig+it.Get());
        }

        //definition du point d'insertion du prochain mini cube
        jOrig+=sub_cube_size;
        //maj du nombre de voxels inseres
        posOrig+=nbVoxInf;
        for(IteratorType it(sub_cube, sub_cube->GetRequestedRegion());
            !it.IsAtEnd(); ++it)
        {
            ScanType::IndexType const & source=it.GetIndex();
            
            ScanType::IndexType destination;
            destination[0] = iOrig+source[0]; 
            destination[1] = jOrig+source[1];
            destination[2] = kOrig+source[2];
            
            cube->SetPixel(destination, posOrig+it.Get());
        }

        //definition du point d'insertion du prochain mini cube
        iOrig+=(sub_cube_size-1);
        kOrig--;
        //maj du nombre de voxels inseres
        posOrig+=nbVoxInf;
        for(IteratorType it(sub_cube, sub_cube->GetRequestedRegion());
            !it.IsAtEnd(); ++it)
        {
            ScanType::IndexType const & source=it.GetIndex();
            
            ScanType::IndexType destination;
            destination[0] = iOrig-source[1]; 
            destination[1] = jOrig+source[2];
            destination[2] = kOrig-source[0];
            
            cube->SetPixel(destination, posOrig+it.Get());
        }

        //le reste du cube est obtenu par symetrie
        for(int i=0;i!=sub_cube_size;i++)
        {
            for(int j=0;j!=cube_size;j++)
            {
                for(int k=0;k!=cube_size;k++)
                {
                    ScanType::IndexType source;
                    source[0] = sub_cube_size-(i+1);
                    source[1] = j;
                    source[2] = k;
                    
                    ScanType::IndexType destination;
                    destination[0] = sub_cube_size+i; 
                    destination[1] = j;
                    destination[2] = k;
                    
                    cube->SetPixel(destination, nbVox-(cube->GetPixel(source)+1));
                }
            }
        }
    }
    
    return cube;
}

template<typename TImage, typename TMask>
void 
HilbertCurveChainGenerator<TImage, TMask>
::_image_scan(std::vector<ImageConstPointer> const & images, MaskConstPointer mask)
{
    unsigned long const scan_length = std::pow(Self::_find_cube_length(images[0]), 3);
    vnl_matrix<double> chain(images.size(), scan_length, 0);
    this->m_MaskChain=vnl_vector<int>(scan_length, 0);
    
    int chain_size=0;

    typedef itk::ImageRegionConstIteratorWithIndex<ImageType> IteratorType;
    for(IteratorType it(images[0], images[0]->GetRequestedRegion());
        !it.IsAtEnd(); ++it)
    {
        typename ImageType::IndexType const & index = it.GetIndex();
        unsigned int const chain_index = this->m_Scan->GetPixel(index);
        
        // Match scan order from Medimax with regular scan order: switch and 
        // mirror the Y and Z axes.
        typename ImageType::SizeType const & size = 
            images[0]->GetRequestedRegion().GetSize();
        typename ImageType::IndexType modified_index;
        modified_index[0] = index[0];
        modified_index[1] = size[2]-index[2]-1;
        modified_index[2] = size[1]-index[1]-1;
    
        for(unsigned int modality=0; modality!=images.size(); modality++)
        {
            chain(modality, chain_index) = images[modality]->GetPixel(modified_index);
        }
        
        // Update MaskChain and chain_size for pixels that are in the mask.
        if(mask.IsNull() || mask->GetPixel(modified_index) != 0)
        {
            this->m_MaskChain[chain_index]=1;
            chain_size++;
        }
    }
    
    // Fill ImageChains only with columns that are in the mask.
    this->m_ImageChains = ImageChainsType(images.size(), chain_size, 0);
    unsigned int column=0;
    for(unsigned int j=0; j!= this->m_MaskChain.size(); ++j)
    {
        if(this->m_MaskChain[j]!=0)
        {
            this->m_ImageChains.set_column(column, chain.get_column(j));
            ++column;
        }
    }
}
