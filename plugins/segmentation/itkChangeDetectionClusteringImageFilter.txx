/*************************************************************************
 * MediPy - Copyright (C) Universite de Strasbourg
 * Distributed under the terms of the CeCILL-B license, as published by
 * the CEA-CNRS-INRIA. Refer to the LICENSE file or to
 * http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
 * for details.
 ************************************************************************/

#ifndef e3abd139_d767_4fa9_97c5_d6ce573e6099
#define e3abd139_d767_4fa9_97c5_d6ce573e6099

#include "itkChangeDetectionClusteringImageFilter.h"

#include <map>
#include <set>
#include <utility>

#include <itkCastImageFilter.h>
#include <itkConstNeighborhoodIterator.h>
#include <itkImageRegionConstIterator.h>
#include <itkImageRegionConstIteratorWithIndex.h>
#include <itkImageRegionIterator.h>
#include <itkHistogram.h>
#include <itkMinimumMaximumImageCalculator.h>
#include <itkThresholdImageFilter.h>

namespace itk
{

template<typename TInputImage, typename TMaskImage, typename TOutputImage>
ChangeDetectionClusteringImageFilter<TInputImage, TMaskImage, TOutputImage>
::ChangeDetectionClusteringImageFilter()
: m_Mask(0), m_MaskBackgroundValue(0), m_Quantile(0.99),
  m_MinimumClusterSize(0),
  m_MaximumNumberOfClusters(std::numeric_limits<unsigned long>::max())
{
}

template<typename TInputImage, typename TMaskImage, typename TOutputImage>
ChangeDetectionClusteringImageFilter<TInputImage, TMaskImage, TOutputImage>
::~ChangeDetectionClusteringImageFilter()
{
    // Nothing to do.
}

template<typename TInputImage, typename TMaskImage, typename TOutputImage>
void
ChangeDetectionClusteringImageFilter<TInputImage, TMaskImage, TOutputImage>
::PrintSelf(std::ostream& os, Indent indent) const
{
    this->Superclass::PrintSelf(os, indent);
    os << indent << "Mask : " << this->m_Mask << "\n";
    os << indent << "Mask background value : " << this->m_MaskBackgroundValue << "\n";
    os << indent << "Quantile : " << this->m_Quantile << "\n";
    os << indent << "Minimum cluster size : " << this->m_MinimumClusterSize << "\n";
    os << indent << "Maximum number of clusters : " << this->m_MaximumNumberOfClusters << "\n";
}

template<typename TInputImage, typename TMaskImage, typename TOutputImage>
void
ChangeDetectionClusteringImageFilter<TInputImage, TMaskImage, TOutputImage>
::GenerateData()
{
    typedef typename InputImageType::IndexType InputIndexType;
    InputImageType const * input = this->GetInput();
    MaskImageType const * mask = this->m_Mask;

    InputImagePixelType const threshold = this->compute_threshold();
    itkDebugMacro(<< "Threshold : " << threshold);

    // Order the voxels based on their intensity. Higher-intensity voxels will
    // be in front.
    typedef std::multimap<InputImagePixelType, InputIndexType,
        std::greater<InputImagePixelType> > Ordering;
    typedef ImageRegionConstIteratorWithIndex<InputImageType> InputImageRegionConstIteratorWithIndexType;
    Ordering ordering;
    for(InputImageRegionConstIteratorWithIndexType it(input, input->GetRequestedRegion());
        !it.IsAtEnd(); ++it)
    {
        InputIndexType const index = it.GetIndex();
        if(input->GetPixel(index) > threshold &&
           mask->GetPixel(index) != this->m_MaskBackgroundValue)
        {
            ordering.insert(std::make_pair(it.Get(), index));
        }
    }
    itkDebugMacro(<< ordering.size() << " voxels in global queue");

    // Use an unsigned long image to avoid problems with float during relabeling.
    typedef Image<unsigned long, InputImageType::ImageDimension> ClustersImageType;
    typedef typename ClustersImageType::Pointer ClustersImagePointer;
    typedef typename ClustersImageType::PixelType ClustersImagePixelType;
    ClustersImagePointer clusters_image = ClustersImageType::New();
    clusters_image->CopyInformation(input);
    clusters_image->SetRegions(input->GetRequestedRegion());
    clusters_image->Allocate();
    clusters_image->FillBuffer(0);
    ClustersImagePixelType clusters_count=0;

    // For each voxel, starting with the highest intensity :
    // * If it has a neighbor in a cluster, add it to this cluster
    // * Otherwise, create a new cluster
    // With this scheme, the label of clusters will be ordered according to the
    // point with the highest likelihood in the cluster.
    
    typedef ConstNeighborhoodIterator<ClustersImageType> NeighborhoodIteratorType;
    typename NeighborhoodIteratorType::RadiusType radius;
    radius.Fill(1);
    NeighborhoodIteratorType nit(radius, clusters_image, clusters_image->GetRequestedRegion());
    for(typename Ordering::const_iterator ordering_it=ordering.begin();
        ordering_it != ordering.end(); ++ordering_it)
    {
        InputIndexType const & index = ordering_it->second;

        nit.SetLocation(index);
        bool new_cluster=true;
        for(unsigned int i=0; i<nit.Size() && new_cluster; ++i)
        {
            typename ClustersImageType::IndexType const neighbor = nit.GetIndex(i);

            if(clusters_image->GetRequestedRegion().IsInside(neighbor) &&
               clusters_image->GetPixel(neighbor) != 0)
            {
                clusters_image->SetPixel(index, clusters_image->GetPixel(neighbor));
                new_cluster=false;
            }
        }

        if(new_cluster)
        {
            ++clusters_count;
            clusters_image->SetPixel(index, clusters_count);
        }
    }
    itkDebugMacro(<< clusters_count << " clusters");

    this->discard_clusters_close_to_mask_boundary<ClustersImageType>(clusters_image);
    this->discard_small_clusters<ClustersImageType>(clusters_image);

    // Only keep a given number of clusters
    typename CastImageFilter<ClustersImageType, OutputImageType>::Pointer
        cast_filter = CastImageFilter<ClustersImageType, OutputImageType>::New();
    cast_filter->SetInput(clusters_image);
    typename ThresholdImageFilter<OutputImageType>::Pointer
        threshold_filter = ThresholdImageFilter<OutputImageType>::New();
    threshold_filter->SetInput(cast_filter->GetOutput());
    threshold_filter->ThresholdAbove(this->m_MaximumNumberOfClusters);

    threshold_filter->GraftOutput(this->GetOutput());
    threshold_filter->Update();
    this->GraftOutput(threshold_filter->GetOutput());
}

template<typename TInputImage, typename TMaskImage, typename TOutputImage>
typename ChangeDetectionClusteringImageFilter<TInputImage, TMaskImage, TOutputImage>::InputImagePixelType
ChangeDetectionClusteringImageFilter<TInputImage, TMaskImage, TOutputImage>
::compute_threshold()
{
    typedef ImageRegionConstIterator<InputImageType> InputConstIteratorType;
    typedef ImageRegionConstIterator<MaskImageType> MaskConstIteratorType;
    // Only keep the top 2% values, based on cumulative histogram

    typedef MinimumMaximumImageCalculator<InputImageType> MinimumMaximumImageCalculator;
    typename MinimumMaximumImageCalculator::Pointer calculator = MinimumMaximumImageCalculator::New();
    calculator->SetImage(this->GetInput());
    calculator->Compute();

    // Compute histogram
    typedef Statistics::Histogram<> Histogram;
    Histogram::Pointer histogram = Histogram::New();
    {
        Histogram::SizeType size; size.Fill(1000);
        Histogram::MeasurementVectorType min; min.Fill(calculator->GetMinimum());
        Histogram::MeasurementVectorType max; max.Fill(calculator->GetMaximum());
        histogram->Initialize(size, min, max);
    }

    if(this->m_Mask.IsNull())
    {
        itkWarningMacro(<<"No mask supplied, using the whole image");

        // Exclude background
        InputConstIteratorType input_it(this->GetInput(),
                                        this->GetInput()->GetRequestedRegion());
        while(!input_it.IsAtEnd())
        {
            if(input_it.Get() != 0)
            {
                histogram->IncreaseFrequency(input_it.Get(), 1);
            }
            ++input_it;
        }
    }
    else
    {
        // Make sure mask is up-to-date
        this->m_Mask->Update();

        InputConstIteratorType input_it(this->GetInput(),
                                        this->GetInput()->GetRequestedRegion());
        MaskConstIteratorType mask_it(this->m_Mask,
                                      this->GetInput()->GetRequestedRegion());

        while(!input_it.IsAtEnd())
        {
            if(mask_it.Get() != this->m_MaskBackgroundValue)
            {
                histogram->IncreaseFrequency(input_it.Get(), 1);
            }
            ++input_it;
            ++mask_it;
        }
    }

    // Find threshold
    return histogram->Quantile(0, this->m_Quantile);
}

template<typename TInputImage, typename TMaskImage, typename TOutputImage>
template<typename TImage>
void
ChangeDetectionClusteringImageFilter<TInputImage, TMaskImage, TOutputImage>
::discard_clusters_close_to_mask_boundary(TImage * image)
{
    typedef TImage ImageType;
    typedef typename ImageType::PixelType PixelType;

    std::set<PixelType> discarded_labels;
    MaskImageType * mask = this->m_Mask;

    // Find labels connected to the mask boundary
    typedef ConstNeighborhoodIterator<ImageType> NeighborhoodIteratorType;
    typename NeighborhoodIteratorType::RadiusType radius;
    radius.Fill(1);

    for(NeighborhoodIteratorType nit(radius, image, image->GetRequestedRegion());
        !nit.IsAtEnd(); ++nit)
    {
        PixelType const center_pixel = nit.GetCenterPixel();

        if(center_pixel == 0)
        {
            // No cluster at this point, skip the neighborhood scan.
            continue;
        }

        for(unsigned int i=0; i<nit.Size(); ++i)
        {
            typename NeighborhoodIteratorType::IndexType const neighbor = nit.GetIndex(i);
            if(mask->GetRequestedRegion().IsInside(neighbor) &&
               mask->GetPixel(neighbor) == this->m_MaskBackgroundValue)
            {
                discarded_labels.insert(center_pixel);
                break;
            }
        }
    }

    // Discard the labels that are connected to the mask boundary
    for(ImageRegionIterator<ImageType> it(image, image->GetRequestedRegion());
        !it.IsAtEnd(); ++it)
    {
        if(discarded_labels.count(it.Get()) != 0)
        {
            it.Set(0);
        }
    }
}

template<typename TInputImage, typename TMaskImage, typename TOutputImage>
template<typename TImage>
void
ChangeDetectionClusteringImageFilter<TInputImage, TMaskImage, TOutputImage>
::discard_small_clusters(TImage * image)
{
    //////////////////////////////////////////
    // Compute the pixel count of all clusters
    //////////////////////////////////////////
    
    typedef typename TImage::PixelType PixelType;
    typedef std::map<PixelType, unsigned long> ClusterSizeMap;
    ClusterSizeMap cluster_size;
    
    typedef itk::ImageRegionConstIterator<TImage> ConstIterator;
    for(ConstIterator it(image, image->GetRequestedRegion()); !it.IsAtEnd(); ++it)
    {
        if(it.Get() == 0)
        {
            continue;
        }
        
        typedef typename ClusterSizeMap::iterator ClusterSizeMapIterator;
        typedef typename ClusterSizeMap::value_type ClusterSizeMapValueType;
        
        std::pair<ClusterSizeMapIterator, bool> const insertion =
            cluster_size.insert(ClusterSizeMapValueType(it.Get(), 0));
        ++insertion.first->second;
    }
    
    //////////////////////////////////////////////////////////////
    // Compute the relabel map:
    // * Small clusters are mapped to background
    // * Large clusters keep their order and get continuous labels
    //////////////////////////////////////////////////////////////
    typedef std::map<PixelType, PixelType> RelabelMap;
    RelabelMap relabel_map;
    PixelType available_label=1;
    for(typename ClusterSizeMap::const_iterator it=cluster_size.begin();
         it != cluster_size.end(); ++it)
    {
        if(it->second < this->m_MinimumClusterSize)
        {
            relabel_map[it->first] = 0;
        }
        else
        {
            relabel_map[it->first] = available_label;
            ++available_label;
        }
    }
    
    ////////////////////
    // Relabel the image
    ////////////////////
    typedef itk::ImageRegionIterator<TImage> Iterator;
    for(Iterator it(image, image->GetRequestedRegion()); !it.IsAtEnd(); ++it)
    {
        it.Set(relabel_map[it.Get()]);
    }
}

}

#endif // e3abd139_d767_4fa9_97c5_d6ce573e6099
