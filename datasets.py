import torch
import os
import json

from torch.utils.data import Dataset
from torch.utils.data.sampler import BatchSampler
from PIL import  Image
import numpy as np

def default_loader(path):
    try:
        img = Image.open(path).convert('RGB')
    except:
        with open('read_error.txt', 'a') as fid:
            fid.write(path+'\n')
        return Image.new('RGB', (224,224), 'white')
    return img

class RandomDataset(Dataset):
    def __init__(self, transform=None, dataloader=default_loader):
        self.transform = transform
        self.dataloader = dataloader

        with open('/home/pqzhuang/data/CUB/CUB_200_2011/val.txt', 'r') as fid:
            self.imglist = fid.readlines()

    def __getitem__(self, index):
        image_name, label = self.imglist[index].strip().split()
        image_path = image_name
        img = self.dataloader(image_path)
        img = self.transform(img)
        label = int(label)
        label = torch.LongTensor([label])

        return [img, label]


    def __len__(self):
        return len(self.imglist)

class BatchDataset(Dataset):
    def __init__(self, transform=None, dataloader=default_loader):
        self.transform = transform
        self.dataloader = dataloader

        with open('/home/pqzhuang/data/CUB/CUB_200_2011/train.txt', 'r') as fid:
            self.imglist = fid.readlines()

        self.labels = []
        for line in self.imglist:
            image_path, label = line.strip().split()
            self.labels.append(int(label))
        self.labels = np.array(self.labels)
        self.labels = torch.LongTensor(self.labels)


    def __getitem__(self, index):
        image_name, label = self.imglist[index].strip().split()
        image_path = image_name
        img = self.dataloader(image_path)
        img = self.transform(img)
        label = int(label)
        label = torch.LongTensor([label])

        return [img, label]


    def __len__(self):
        return len(self.imglist)

class MVIDataset(Dataset):
    def __init__(self, kind, fold, transform):
        self.kind = kind
        self.fold = fold
        self.transform = transform
        self._get_data()
        self.lables = np.array(self.labels)
        self.labels = torch.LongTensor(self.labels)
        # print(self.labels)
        # assert 0
    def _get_data(self):
        json_file = 'crop_' + self.kind + '_fold' + str(self.fold) + '.json'
        with open(os.path.join('/media/data/ilab/lxy_media/MVI_grading_2023/data/folds', json_file), 'r') as inf:
            data_dic = json.load(inf)
        self.labels = list()
        self.filenames = list()
        self.subjects = list()
        self.layers = list()
        for key, value in data_dic.items():
            _, classes = key.split('M')
            for i in range(3):
                self.layers.append(i)
                self.labels.append(int(classes))
                self.filenames.append(value['T1'].split('.')[0])
                self.subjects.append(key)

    def __getitem__(self, index):
        file_name= self.filenames[index]
        label = np.array(self.labels[index]).astype(np.int64)
        file_name = f'{file_name}_{str(self.layers[index])}.jpg'
        image = Image.open(os.path.join('/media/data/ilab/lxy_media/MVI_grading_2023/data/crop_img_224', file_name)).convert('RGB')
        image = self.transform(image)
        return [image, label]
    
    def __len__(self):
        return len(self.filenames)


class BalancedBatchSampler(BatchSampler):
    def __init__(self, dataset, n_classes, n_samples):
        self.labels = dataset.labels
        self.labels_set = list(set(self.labels.numpy()))
        self.label_to_indices = {label: np.where(self.labels.numpy() == label)[0]
                                 for label in self.labels_set}
        for l in self.labels_set:
            np.random.shuffle(self.label_to_indices[l])
        self.used_label_indices_count = {label: 0 for label in self.labels_set}
        self.count = 0
        self.n_classes = n_classes
        self.n_samples = n_samples
        self.dataset = dataset
        self.batch_size = self.n_samples * self.n_classes

    def __iter__(self):
        self.count = 0
        while self.count + self.batch_size < len(self.dataset):
            classes = np.random.choice(self.labels_set, self.n_classes, replace=False)
            indices = []
            for class_ in classes:
                indices.extend(self.label_to_indices[class_][
                               self.used_label_indices_count[class_]:self.used_label_indices_count[
                                                                         class_] + self.n_samples])
                self.used_label_indices_count[class_] += self.n_samples
                if self.used_label_indices_count[class_] + self.n_samples > len(self.label_to_indices[class_]):
                    np.random.shuffle(self.label_to_indices[class_])
                    self.used_label_indices_count[class_] = 0
            yield indices
            self.count += self.n_classes * self.n_samples

    def __len__(self):
        return len(self.dataset) // self.batch_size
